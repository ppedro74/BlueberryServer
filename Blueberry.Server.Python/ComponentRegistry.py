
class ComponentRegistry:
    Components = dict()

    def register_component(key, component):
        ComponentRegistry.Components[key] = component

    def get_component(key):
        return None if key not in ComponentRegistry.Components else ComponentRegistry.Components[key]
