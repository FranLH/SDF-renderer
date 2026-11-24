#version 430



in vec2 uv;
out vec4 fragColor;


uniform vec2 resolution;
uniform float time;
uniform int objectCount;
uniform int MAX_STEPS;
uniform bool SHADOWS_ENABLED;
uniform vec3 light_source_pos;

const float MAX_DISTANCE = 1000.0;


uniform int FOV;
uniform vec3 camPos;
uniform vec3 orientation;

const vec3 colors1[3] = vec3[]( // Dark color
vec3(0.1,0.6,0.2), // Green
vec3(0.6, 0.1, 0.0), // Red
vec3(0.0, 0.4, 0.6)); // Blue

const vec3 colors2[3] = vec3[]( // Light color
vec3(0.3,0.8,0.1),
vec3(0.8,0.3,0.1),
vec3(0.0, 0.6, 0.9));

float SdfBox( vec3 p, vec3 b )
{
  vec3 d = abs(p) - b;
  return min(max(d.x,max(d.y,d.z)),0.0) +
         length(max(d,0.0));
}

float SdfSphere(vec3 p, float r) // return (cos(p.x/100) + sin(p.y/100) - cos(p.z/100))*100; // weird infinite structure
{
	
	return length(p) - r;  //return length(p) - r;
}


struct SDFObject
{
	ivec4 info; // (type, color, operation type, operationObjID)
	vec4 position; // z is always 0
	vec4 data; // (radius, x, y, z)
};

// If operation type isn't 0, the object gets skipped from normal calculations.
// If operationObjID isn't 0, then this is the start of an operation chain.
// On such a chain, each object contains its own operation type, and the ID of the next operation in the chain.
// If the next operation ID is equal to its own ID, then it's the end of the chain.

layout(std430, binding = 1) buffer SDFObjects
{
    SDFObject objects[];
};

float EvaluateObject(SDFObject object, vec3 pos)
{
	vec3 localPos = pos - object.position.xyz;

	if (object.info.x == 0)
	{
		return SdfSphere(localPos, object.data.x);
	}
	if (object.info.x == 1)
	{
		return SdfBox(localPos, object.data.yzw);
	}

	return 1e5; // Exception if object type is invalid
}

float ApplyOperations(float baseDist, int objID, vec3 rayPos)
{
	SDFObject obj = objects[objID];
	int operation;
	int nextOperationID;
	float dist;

	for (int i=0; i < 16; i++)
	{
		operation = obj.info.z;
		nextOperationID = obj.info.w;
		dist = EvaluateObject(obj, rayPos);
		if (operation == 1) // Subtraction
		{
			dist = max(baseDist, -dist);
		}	
		else if (operation == 2) // Intersection
		{
			dist = max(baseDist, dist);
		}
		if (obj.info.w != objID) // If there are more operations in the chain
		{
			baseDist = dist;
			objID = nextOperationID;
			obj = objects[objID];
		}
		if (nextOperationID == objID) break;
	}
	// while (nextOperationID != objID)
	// {
	// 	dist = EvaluateObject(obj, rayPos);
	// 	if (operation == 1) // Subtraction
	// 	{
	// 		dist = max(baseDist, -dist);
	// 	}	
	// 	else if (operation == 2) // Intersection
	// 	{
	// 		dist = max(baseDist, dist);
	// 	}
	// 	if (obj.info.w != objID) // If there are more operations in the chain
	// 	{
	// 		baseDist = dist;
	// 		objID = nextOperationID;
	// 		obj = objects[objID];
	// 	}
	// }
	dist = EvaluateObject(obj, rayPos);
	if (operation == 1) // Subtraction
	{
		dist = max(baseDist, -dist);
	}
	else if (operation == 2) // Intersection
	{
		dist = max(baseDist, dist);
	}

	return dist;
}

vec3 calculateColor(bool hit, vec3 hitPos, bool escaped, int colorID)
{
	vec3 col;
	if (escaped)
	{
		col = vec3(0.0,1.0,1.0);
	}
	else if (hit)
	{
		if (sin(hitPos.x/2) + sin(hitPos.y/2) + sin(hitPos.z/2) < 0)
		{
			col = colors1[colorID];
		}
		else
		{
			col = colors2[colorID];
		}
	}
	else // Ran out of steps
	{
		col = vec3(0.0,0.0,0.0); // sky color
	}
	return col;
}




mat4 CamToWorldMatrix(vec3 translation, vec3 forward)
{
	vec3 right = normalize(cross(vec3(0.0,1.0,0.0), forward));
	vec3 up = normalize(cross(forward,right));
	return mat4(vec4(right, 0.0), vec4(up, 0.0), vec4(forward, 0.0), vec4(translation, 1.0	));
}


void main()
{
	float epsilon = 0.01;
	int steps = 0;
	vec2 UV = (uv - 0.5) * vec2(resolution.x / resolution.y, 1.0); // Accounted for image aspect ratio and centering. Inverts Y
	vec3 rayPos = camPos; // Ray origin
	vec3 rayDirection = vec3(UV * tan(radians(float(FOV))/2), 1.0); // Ray direction
	rayDirection = normalize(mat3(CamToWorldMatrix(camPos, normalize(orientation))) * rayDirection);

	float minDist;
	int closest = 0;
	while (steps<MAX_STEPS)
	{
		minDist = 1e5;
		
		for (int i = 0; i < objectCount; i++)
		{
			if (objects[i].info.z != 0)
			{
				continue;
			}
			float dist = EvaluateObject(objects[i], rayPos);
			if (objects[i].info.w != 0)
			{
				dist = ApplyOperations(dist, objects[i].info.w, rayPos);
			}

			if (dist < minDist)
			{
				closest = i;
				minDist = dist;
			}
		}
		if (minDist < epsilon || minDist > MAX_DISTANCE)
		{
			break;
		}

		rayPos+=rayDirection*minDist;
		steps+=1;
	}
	rayPos-=rayDirection*epsilon; // Push back to avoid shadow problems. Would be better to push in the direction of the normal

	vec3 col = calculateColor(steps<MAX_STEPS, rayPos, minDist>MAX_DISTANCE, objects[closest].info.y);



	if (SHADOWS_ENABLED && minDist<=epsilon)
	{
		float epsilon = 0.0001;
		int steps = 0;
		vec3 shadowRayPos = rayPos; // Ray origin
		vec3 rayDirection = normalize(-rayPos+light_source_pos); // Ray direction
		float maxDist = distance(rayPos, light_source_pos);
		//shadowRayPos += rayDirection*(epsilon*5);
		float len = 0;
		while (steps<100)
		{
			minDist = 1e5;
			
			for (int i = 0; i < objectCount; i++)
			{
				if (objects[i].info.z != 0)
				{
					continue;
				}
				float dist = EvaluateObject(objects[i], shadowRayPos);
				if (objects[i].info.w != 0)
				{
					dist = ApplyOperations(dist, objects[i].info.w, shadowRayPos);
				}
				if (dist < minDist)
				{
					minDist = dist;
				}
			}
			if (minDist < epsilon || minDist > MAX_DISTANCE)
			{
				break;
			}

			shadowRayPos+=rayDirection*minDist;
			len += minDist;
			steps+=1;
		}
		//float darkness = distance(shadowRayPos, rayPos);
		if (minDist < epsilon) // If the light source gets blocked by any object
		{
			col *= min(0.5*(max((5*len/maxDist), 1)), 1); // FIX
		}
		// else
		// {
		// 	col *= min((0.5/min(closest, 1.0)), 1.0) ;
		// }
	}

	
	fragColor = vec4(col, 1.0);
}