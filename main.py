import moderngl_window as mglw
import glfw
import math
import numpy as np



class Cam:
    def __init__(self, pos, rotation, orientation, fov):
        self.pos, self.orientation, self.fov = pos, orientation, fov
        self.rotation = rotation # [yaw, pitch]
        self.UpdateOrientation()
    def Forward(self, yaw, pitch):
        return [
        math.sin(yaw) * math.cos(pitch),
        math.sin(pitch),
        math.cos(yaw)*math.cos(pitch)]
    def HForward(self,yaw):
        return [
        math.sin(yaw),
        0,
        math.cos(yaw)]

    def UpdateOrientation(self): # yaw: around global Y axis, pitch: around local right axis
        self.rotation[1] = min(max(self.rotation[1],-89), 89)
        yaw = math.radians(self.rotation[0])
        pitch = math.radians(self.rotation[1])
        self.orientation = self.Forward(yaw, pitch)
        self.hright = self.HForward(yaw+math.pi/2)
        self.hforward = self.HForward(yaw)
        

object_dtype = np.dtype([
("info", "4i4"),
("position", "4f4"),
("data", "4f4")])
objects = np.zeros(4, dtype=object_dtype)

# Medium blue ball, the other one follows it
objects[0]["info"] = (0,2,0,0) # Is modified by element #1
objects[0]["position"] = (0,0,50,0)
objects[0]["data"] = (10,0,0,0)

# This is a big green wall
objects[1]["info"] = (1,0,0,2) # Has difference operator. Is modified by element #2
objects[1]["position"] = (20,-10,30,0)
objects[1]["data"] = (0,10,70,80)

# This is an inverse sphere
objects[2]["info"] = (0,0,1,2)
objects[2]["position"] = (0,-25,70,0)
objects[2]["data"] = (50,0,0,0)

objects[3]["info"] = (1,1,0,2)
objects[3]["position"] = (0,-40,10,0)
objects[3]["data"] = (20,200,30,200)



class App(mglw.WindowConfig):
    window_size = [1440,900]
    fullscreen = False
    vsync = False 
    
    resource_dir = 'Shaders'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wnd.mouse_exclusivity = True
        #self.wnd.fullscreen = False
        print(type(self.wnd))
        print(self.wnd.name)
        
        self.main_texture = self.ctx.texture(self.window_size, components=4)# 8-bit normalized
        self.main_texture.filter = (self.ctx.LINEAR, self.ctx.LINEAR)
        
        self.main_fbo = self.ctx.framebuffer(color_attachments = [self.main_texture])
        
        self.quad = mglw.geometry.quad_fs()
        
        self.prog = self.load_program(vertex_shader='vertex_shader.glsl', fragment_shader='fragment_shader_2.glsl')
        self.set_uniform("objectCount", len(objects))
        

        #self.set_uniform('resolution', self.window_size)
#         self.set_uniform('inColor', insideColor)
#         self.set_uniform('outPalette', outsideColorPalette)
#         self.set_uniform('paletteSize', len(outsideColorPalette))
        
        
        self.post_prog = self.load_program(vertex_shader='vertex_shader.glsl', fragment_shader='post_processing.glsl')
#         self.post_prog['blurStrength'] = blurStrength
#         self.post_prog['mandelTex'] = 0
#         self.post_prog['resolution'] = self.window_size
        
        # -------------- CONFIG -------------------
        self.camera = Cam([0, 0, 0], [0,0], [0, 0, 1], 90)

        self.moveSpeed=1
        self.rotateSpeed = 0.1
        self.maxSteps = 200
        # -----------------------------------------
        
        self.keyStates = {
        "W" : False,
        "A" : False,
        "S" : False,
        "D" : False,
        "UP" : False,
        "DOWN" : False,
        "SHIFT" : False,
        "SPACE" : False}
        self.mouseMovement = [0,0]
        

        
        self.sdf_buffer = self.ctx.buffer(
        reserve=objects.nbytes,
        dynamic=True)
        self.sdf_buffer.write(objects.tobytes())
        self.sdf_buffer.bind_to_storage_buffer(1)

        #self.set_uniform("MAX_STEPS", self.maxSteps)
        self.on_resize(*self.wnd.buffer_size) # Updates window size at the start
        

        
    def on_mouse_position_event(self, x, y, dx, dy):
        #print(x, y, dx, dy)
        self.mouseMovement = [dx,dy]
        self.camera.rotation[0]+=dx*self.rotateSpeed
        self.camera.rotation[1]-=dy*self.rotateSpeed
        self.camera.UpdateOrientation()
    
    def set_uniform(self, u_name, u_value):
        try:
            self.prog[u_name] = u_value
        except KeyError:
            #print(f'uniform: {u_name} - not used in shader')
            pass
    def on_resize(self,width, height):
        self.window_size = [width, height]
        self.render_size = [width, height]
        
        self.ctx.viewport = (0, 0, width, height)
        self.set_uniform('resolution', self.window_size)
        
        self.main_texture.release() # Clears the texture from memory
        self.main_fbo.release() # Clears the framebuffer from memory

        self.main_texture = self.ctx.texture(self.render_size, components=4) # Creates the texture again
        self.main_fbo = self.ctx.framebuffer(color_attachments=[self.main_texture]) # Creates the framebuffer again


    def on_render(self, time, frame_time):
        w, h = self.window_size
        
        objects[0]["position"][0]+=2*math.sin(time)
        objects[0]["position"][2]+=math.cos(time)
        objects[2]["position"] = objects[0]["position"]
        self.sdf_buffer.write(objects.tobytes())
        
        #self.sdf_buffer.bind_to_storage_buffer(1)
        
        if self.keyStates["W"]:
            self.camera.pos[0]+=self.camera.hforward[0]*self.moveSpeed
            self.camera.pos[2]+=self.camera.hforward[2]*self.moveSpeed
        if self.keyStates["S"]:
            self.camera.pos[0]-=self.camera.hforward[0]*self.moveSpeed
            self.camera.pos[2]-=self.camera.hforward[2]*self.moveSpeed
        if self.keyStates["D"]:
            self.camera.pos[0]+=self.camera.hright[0]*self.moveSpeed
            self.camera.pos[2]+=self.camera.hright[2]*self.moveSpeed
        if self.keyStates["A"]:
            self.camera.pos[0]-=self.camera.hright[0]*self.moveSpeed
            self.camera.pos[2]-=self.camera.hright[2]*self.moveSpeed
        if self.keyStates["SHIFT"]:
            self.camera.pos[1]-=self.moveSpeed
        if self.keyStates["SPACE"]:
            self.camera.pos[1]+=self.moveSpeed
        
        #------------------------------------------------------
        self.main_fbo.use() # Pass 1
        self.ctx.viewport = (0, 0, w, h)
        self.ctx.clear()
        
#         self.set_uniform('DEPTH', self.depth)
        self.set_uniform('time', time)
        self.set_uniform('MAX_STEPS', self.maxSteps)
#         self.set_uniform('zoom', self.camera.zoom)
        self.set_uniform('camPos', self.camera.pos)
        self.set_uniform('orientation', self.camera.orientation)
        self.set_uniform('FOV', self.camera.fov)
#         self.set_uniform('fractalPos', self.fractalOrigin)
        
        
        self.quad.render(self.prog)
        #-------------------------------------------------
        self.ctx.screen.use() # Pass 2
        self.ctx.viewport = (0, 0, w, h)
        self.ctx.clear()

        self.main_texture.use(location=0)
        self.quad.render(self.post_prog)
        
        
    def on_key_event(self, key, action, modifiers):
        keys = self.wnd.keys
        
        #if action == self.wnd.keys.ACTION_PRESS:
        if key == self.wnd.keys.P:
            print("position:", self.camera.pos)
            print("orientation:", self.camera.orientation)

        if key == self.wnd.keys.H:
            self.camera.pos = [0,0,0]
            self.camera.orientation = [0,0,0]
        if key == self.wnd.keys.W:
            self.keyStates["W"] = True if action == keys.ACTION_PRESS else False if action == keys.ACTION_RELEASE else self.keyStates["W"]
        if key == self.wnd.keys.S:
            self.keyStates["S"] = True if action == keys.ACTION_PRESS else False if action == keys.ACTION_RELEASE else self.keyStates["S"]
        if key == self.wnd.keys.D:
            self.keyStates["D"] = True if action == keys.ACTION_PRESS else False if action == keys.ACTION_RELEASE else self.keyStates["D"]
        if key == self.wnd.keys.A:
            self.keyStates["A"] = True if action == keys.ACTION_PRESS else False if action == keys.ACTION_RELEASE else self.keyStates["A"]
        if key == self.wnd.keys.LEFT_SHIFT:
            self.keyStates["SHIFT"] = True if action == keys.ACTION_PRESS else False if action == keys.ACTION_RELEASE else self.keyStates["SHIFT"]
        if key == self.wnd.keys.SPACE:
            self.keyStates["SPACE"] = True if action == keys.ACTION_PRESS else False if action == keys.ACTION_RELEASE else self.keyStates["SPACE"]


if __name__ == '__main__':
    mglw.run_window_config(App, args=["--window", "glfw"])


    