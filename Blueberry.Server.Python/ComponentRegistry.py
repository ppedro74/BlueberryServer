import Controller

class ComponentRegistry:
    Components = dict()
    Controllers = []

    def register_component(key, component):
        ComponentRegistry.Components[key] = component

    def get_component(key):
        return None if key not in ComponentRegistry.Components else ComponentRegistry.Components[key]

    def register_controller(controller):
         if not isinstance(controller, Controller.Controller):
             raise TypeError("not a controller")
         ComponentRegistry.Controllers.append(controller)

