import gmsh, sys, time
name = sys.argv[1]
gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
gmsh.merge(f'work/rem_{name}.stl')
s=gmsh.model.getEntities(2)
l=gmsh.model.geo.addSurfaceLoop([e[1] for e in s]); v=gmsh.model.geo.addVolume([l]); gmsh.model.geo.synchronize()
gmsh.option.setNumber("Mesh.Algorithm3D",1)
gmsh.option.setNumber("Mesh.MeshSizeMax",5)
t=time.time(); gmsh.model.mesh.generate(3)
gmsh.model.mesh.setOrder(2)
et,tags,_=gmsh.model.mesh.getElements(3)
print(name,'tets',sum(len(x) for x in tags),'time',round(time.time()-t,1))
gmsh.model.addPhysicalGroup(3,[v],1)
gmsh.write(f'work/mesh_{name}.msh'); gmsh.finalize()
