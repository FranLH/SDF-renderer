#version 330

uniform sampler2D mandelTex;
uniform vec2 resolution;

uniform float blurStrength;

in vec2 uv;
out vec4 fragColor;

void main() {
    vec2 texel = 1.0 / resolution;

    vec3 color = texture(mandelTex, uv).rgb;

    // Example: simple blur (Averages between the eight surrounding pixels)

    float darkEdge = max(distance(uv, vec2(0.5,0.5)) * 2 ,1 );
    //color = max(color,1.6*color-0.25); // Make bright colors pop
    color/=darkEdge;

    fragColor = vec4(color, 1.0);
    
}
