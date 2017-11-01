
# FACT INTEGRATION KERNEL SERVER
The kernel ([Olov Nykvist](onykvist@kth.se)) is the server operating between "The Architecture" ([TMH, Dimosthenis Kontogiorgos](diko@kth.se)), the Hololens module ([Elena Sibirtseva](elenasi@kth.se)) and the underlying ROS-network ([Hakan Karaoguz, et al.](hkarao@kth.se)).


![Graph overview of the system](/system_graph.jpg)

Graph overview of the system

### Message declarations
All messages through the server begins with the name of the recipient client (client type) followed by a ";".

#### Update message to the interpreter
Update the position and color of the *n* blocks closest to the coordinates given.
~~~
interpreter;block_1;block_2; ... ;block_n
~~~
where `block_n` can have one of the following forms:
~~~
x_pos, y_pos
x_pos, y_pos, color:color_value
x_pos, y_pos, size:size_value
x_pos, y_pos, color:color_value, size:size_value
x_pos, y_pos, size:size_value, color:color_value
~~~
Example:
~~~
interpreter;0.43,0.33,color:red;0.55,0.21,size:small
~~~