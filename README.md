# ECS-python
An implementation of Entity Component System in python using pygame

# Usage:  
### Bare minimum needed to get started
```py
from ECS import Game

TestGame = Game()
TestGame.Run()
```

### Basic game example with a system
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
TestGame.AddEntity()                            \
        .AddComponent(Position(x=50,y=50))      \
        .AddComponent(Velocity(x=2,y=-1))       \
        .AddComponent(Renderable(sprite="player.png"))
TestGame.Run()
``` 
### Example with threaded system
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

TestGame.AddEntity()                           \                
        .AddComponent(Position(x=50,y=50))     \        
        .AddComponent(Velocity(x=0.5,y=0.5))   \          
        .AddComponent(Renderable(sprite='player.png'))

TestGame.Run()
```
