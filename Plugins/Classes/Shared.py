

__all__ = [
    'Physics_Properties',
    ]

class Physics_Properties:
    '''
    Adds physics related methods to a class macro.
    A user macro should inherit from this, but doesn't need to call init.
    '''    
    def Get_Forward_Drag(self):
        'Return the object forward drag.'
        return float(self.Get('./properties/physics/drag', 'forward', default = '1'))

    def Adjust_Speed(self, multiplier):
        '''
        Adjust the speed and acceleration of this object based on the
        given multiplier.
        This applies the inverse multiplier to the object's drag and mass.
        '''
        # The fields to change are scattered under the physics node.        
        path_attrs = [
            ('./properties/physics', 'mass'),
            ('./properties/physics/drag', 'forward'),
            ('./properties/physics/drag', 'reverse'),
            ('./properties/physics/drag', 'horizontal'),
            ('./properties/physics/drag', 'vertical'),
            ]

        for path, attr in path_attrs:
            value = float(self.Get(path, attr, default = '1'))
            new_value = value / multiplier
            self.Set(path, attr, f'{new_value:0.4f}')
        return

    
    def Adjust_Turning(self, multiplier):
        '''
        Adjust the turning rate of this object based on the given multiplier.
        This applies the inverse multiplier to the object's inertia.
        '''
        path_attrs = [
            ('./properties/physics/inertia', 'pitch'),
            ('./properties/physics/inertia', 'yaw'),
            ('./properties/physics/inertia', 'roll'),
            ]
        
        for path, attr in path_attrs:
            value = float(self.Get(path, attr))
            new_value = value / multiplier
            self.Set(path, attr, f'{new_value:0.4f}')
        return
