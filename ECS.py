###########Description#############
"""
#####An implementation of **Entity Component System** in python with pygame </br></br>
#####Usage:  </br>
* Bare minimum needed to get started
```py
from ECS import Game

TestGame = Game()
TestGame.Run()
```

* Basic game example with a system
```py
from ECS import Game, Vector2d, Renderable

class Position (Vector2d): pass
class Velocity (Vector2d): pass
#creates component type [Position] and [Velocity] from existing component [Vector2d]

def MovementSystem(positionComponents : list[Position], velocityComponents : list[Velocity]):
    for pos,velo in zip(positionComponents, velocityComponents):
        pos.x += velo.x 
        pos.y += velo.y

TestGame = Game()
TestGame.AddSystem(MovementSystem)
TestGame.AddEntity()                            \\
        .AddComponent(Position(x=50,y=50))      \\
        .AddComponent(Velocity(x=2,y=-1))       \\
        .AddComponent(Renderable(sprite="player.png"))
TestGame.Run()
``` 
* Example with threaded system
```py
from ECS import Game, Vector2d, Renderable

TestGame = Game()

class Position (Vector2d): pass
class Velocity (Vector2d): pass

@TestGame.ThreadedSystem(CallRate=60) #System which is called 60 times per second
def MovementSystem(positionComponents : list[Position], velocityComponents : list[Velocity]):
    for pos,velo in zip(positionComponents, velocityComponents):
        pos.x += velo.x 
        pos.y += velo.y

@TestGame.MainThreadSystem
def RenderSystem(positionComponents : list[Position], renderableComponents : list[Renderable]):
    for pos,renderable in zip(positionComponents, renderableComponents):
        TestGame.screen.blit(renderable.sprite, pos.ToTuple())

TestGame.AddEntity()                           \\                
        .AddComponent(Position(x=50,y=50))     \\        
        .AddComponent(Velocity(x=0.5,y=0.5))   \\          
        .AddComponent(Renderable(sprite='player.png'))

TestGame.Run()
```
"""
###################################

##############imports##############
from __future__ import annotations
import pygame
from functools import lru_cache
from threading import Thread
import time
pygame.init()
###################################

#######Entity and Components#######
class Entity:
    __ID_COUNT__ = 0
    """
A container which holds an id and a list of components </br>
A combination of components should allow for creation of any object from traditional game systems
"""
    def __init__(self, AddComponentEvent = lambda x : (), RemoveComponentEvent = lambda x : ()) -> None:
        self.components : dict = {}
        self.AddComponentEvent = AddComponentEvent
        self.RemoveComponentEvent = RemoveComponentEvent
        self.id = Entity.__ID_COUNT__
        Entity.__ID_COUNT__ += 1

    def AddComponent(self, component) -> Entity:
        self.components[component.__class__] = component
        self.AddComponentEvent(self)
        return self
    def RemoveComponent(self, component_class) -> Entity:
        self.components.pop(component_class)
        self.RemoveComponentEvent(self)
        return self

class Vector2d:
    """Simple Vector component"""
    def __init__(self,x,y) -> None:
        self.x = x
        self.y = y

    def ToTuple(self) -> tuple:
        """Returns the x-y values of the Vector component in tuple form **(x,y)**"""
        return (self.x, self.y)

class Renderable:
    """
Component which stores a sprite for the entity. </br>
- **Dependencies**: [ <a href="#Vector2d">Vector2d</a> ]
"""
    __dependencies__ = []
    def __init__(self, sprite : str) -> None:
        self.sprite = LoadImage(sprite)
###################################


#############Systems###############
class System:
    """
**Not to be created directly**</br>
- Contains a single function and the corresponding components which will be fed into the system every call  </br>
- A system is a function which is ran every frame unless it is on another thread </br>
- The parameter's types will define what components it will be given access to </br>
- This is better understood through an example : 
```py
def MovementSystem(positionComponents : list[Position], velocityComponents : list[Velocity]):
    # positionComponents and velocityComponents are lists of the specified component types
    for pos,velo in zip(positionComponents, velocityComponents):
        # zip() turns ( (pos1, pos2), (velo1, velo2) ) into ((pos1, velo1), (pos2, velo2), ....)
        # allowing you to iterate through them entity by entity
        pos.x += velo.x 
        pos.y += velo.y
        # adds velocity to the current position
```
    """
    def __init__(self, SystemFunction, query : list) -> None:
        self.__func__ = SystemFunction
        self.__query__ : list = self._extract_queries_(query)

        self.Components : list[list] = [[] for _ in range(len(self.__query__))]
        self.entities : list[int] = []
        """ List which stores relevant Components in list form: </br> **[type1 = [component1, component2, ...], type2 = [component1, component2, ...], ...]**"""

    def __add_components_from_entity__(self, entity : Entity) -> System:
        for idx,class_type in enumerate(self.__query__):
            self.Components[idx].append(entity.components[class_type])
        self.entities.append(entity.id)
        return self

    def __remove_entity__(self, entity_id : int) -> System:
        index = self.entities.index(entity_id)
        for class_list in self.Components:
            class_list.pop(index)
        self.entities.remove(entity_id)
        return self

    def IsEntityCompatible(self, entity : Entity) -> bool:
        """Checks the components an entity has, and returns true if it has all the component types from a query, otherwise returns false"""
        return all([x in entity.components for x in self.__query__])

    def _extract_queries_(self, query_types) -> list:
        try:
            result = []
            for query_type in query_types:
                if query_type.__origin__ == list:
                    query = query_type.__args__[0]
                    if query in result: raise ValueError
                    result.append(query)
            return list(result)
        except ValueError:
            print("Attempted to add query twice!")
        

    def __call__(self, *args, **kwargs):
        self.__func__(*args,**kwargs)

class SystemThread:
    """
**Not to be created directly**</br>
- Contains a list of systems which are to be ran off the main system and onto another thread </br>
- Calling a SystemThread object as if it were a function will start up the thread
"""
    def __init__(self, rate=144) -> None:
        self.__systems__ : list[System] = []
        self.__call_rate__ = rate
        self.__call_interval__ = (1/rate)
        self.__stop__ = True

    def __thread__(self):
        self.__stop__ = False
        while True:
            for system in self.__systems__:
                system(*system.Components)
            if self.__stop__: return
            time.sleep(self.__call_interval__)
            
    def __call__(self):
        thread = Thread(target=self.__thread__, daemon=True)
        thread.start()

    def Stop(self) -> None:
        """stops thread if it is running"""
        if self.__stop__ == False: self.__stop__ == True


    def AddSystem(self, function) -> SystemThread:
        """Adds a system onto this thread. must pass in a **function** and not a <a href= "#System">System</a> object"""
        self.__systems__.append(System(function,function.__annotations__.values()))
        return self


class SystemManager:
    """
**Not to be created directly, only to be inherited by <a href="#Game">Game</a> class**</br>
- Handles systems, entities, and addition of new system threads
"""
    def __init__(self) -> None:
        self.__main_thread_systems__ : list[System] = []
        self.__off_thread_systems__ : list[SystemThread] = []
        self.__entities__ : dict[int, Entity] = {}

    def MainThreadSystem(self, function):
        """Decorator which is equivalent to <a>SystemManager.AddSystem</a>"""
        self.AddSystem(function)

    def AddSystem(self, function) -> SystemManager:
        """Adds a system onto the main thread. must pass in a **function** and not a <a href= "#System">System</a> object"""
        new_system = System(function,function.__annotations__.values())
        for entity in self.__entities__.values():
            self.SortIntoSystem(entity, new_system)
        self.__main_thread_systems__.append(new_system)
        return self

    def ThreadedSystem(self, CallRate = 144):
        """
**Don't forget to call it : @[Game obj here].ThreadedSystem()**</br>
- Decorator for the <a>SystemManager.AddThreadedSystem</a> method
"""
        def decorator(func):
            self.AddThreadedSystem(func, CallRate = CallRate)
        return decorator

    def AddThreadedSystem(self, function, CallRate = 144) -> SystemManager:
        """
        Adds a system off the main thread. must pass in a **function** and not a <a href= "#System">System</a> object </br>
        - CallRate can be thought of as the *frame rate* for the system</br>
        - (CallRate=144 would mean that the system is called 144 times per second)
        """
        for system_thread in self.__off_thread_systems__: #attempt to find a thread which has the same call rate
            if system_thread.__call_rate__ == CallRate:
                system_thread.AddSystem(function) #if found, add the system to this existing thread
                return self

        new_thread = SystemThread(rate=CallRate) #otherwise, make a new system thread with the specified call rate
        new_thread.AddSystem(function) #add the system to this new system thread
        self.__add_system_thread_(new_thread) #add this system thread to the Game

    def __add_system_thread_(self, system_thread : SystemThread, StartThread=True) -> SystemManager:
        self.__off_thread_systems__.append(system_thread)
        if StartThread: system_thread() #starts thread
        return self

    def __tick_systems__(self) -> SystemManager:
        """Will call all the systems on the main thread"""
        for system in self.__main_thread_systems__:
            system(*system.Components)
        return self

    def SortEntity(self, entity : Entity) -> None:
        """iterates through all systems and checks if entity fits the system's query"""
        for system in self.__main_thread_systems__:
            self.SortIntoSystem(entity, system)
        for thread in self.__off_thread_systems__:
            for system in thread.__systems__:
                self.SortIntoSystem(entity, system)

    def SortIntoSystem(self, entity : Entity, system : System):
        """Attempts to insert entity's compatible components into the system if they match the query or remove components if player no longer fits the query"""
        if system.IsEntityCompatible(entity):
            if not (entity.id in system.entities):
                system.__add_components_from_entity__(entity)
        else :
            if entity.id in system.entities:
                system.__remove_entity__(entity.id)


    def AddEntity(self) -> Entity:
        entity = Entity(AddComponentEvent=self.SortEntity, RemoveComponentEvent=self.SortEntity)
        self.__entities__[entity.id] = entity
        return entity
###################################

##############Pygame + System integration###################
class Game(SystemManager):
    """Pygame wrapper that implements entity component system"""
    def __init__(self, WindowSize = (700, 500), fps = 144, title = "Template") -> None:
        super().__init__()
        self.WINDOW_SIZE = WindowSize
        self.FPS = fps
        self.screen = None
        self.clock = None
        self.title = title

    def Run(self) -> None:
        """Creates a window and starts up the game (systems are started)"""
        self.screen = pygame.display.set_mode(self.WINDOW_SIZE, pygame.DOUBLEBUF | pygame.HWSURFACE)
        self.controllers = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        pygame.display.set_caption(self.title)
        carryOn = True
        self.clock = pygame.time.Clock()
        while carryOn:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    carryOn = False
            self.screen.fill(Color.BLACK)
            self.__tick_systems__()
            pygame.display.flip()
            self.clock.tick(self.FPS)
        pygame.quit()
############################################################

############# utils ###############
@lru_cache(maxsize=100)
def LoadImage(path : str):
    """loads an image in pygame format. caches image if it is already loaded once"""
    return pygame.image.load(path)

class Color():
    """- Contains constants of colors in tuple form **(r,g,b)**"""
    BLACK  = ( 0, 0, 0)
    WHITE  = ( 255, 255, 255)

    RED    = ( 255, 0, 0)
    GREEN  = ( 0, 255, 0)
    BLUE   = ( 0, 0, 255)

    YELLOW = ( 204, 255, 51 )
    PURPLE = ( 153, 0, 204  )
    BROWN  = ( 153, 102, 51 )
    PINK   = ( 255, 0, 102  )
    LIME   = ( 108, 218, 0  )
###################################