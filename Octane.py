
import os
import bpy
from . import DtbMaterial
from . import Global
from . import NodeArrange
from . import Versions
from . import MatDct
from . import Util
NGROUP3 = ['oct_skin','oct_eyewet','oct_eyedry']
SKIN = 0
EWET = 1
EDRY = 2
def ngroup3(idx):
    return NGROUP3[idx] + Util.get_dzidx()

class Octane:
    ftable = [["d", "Diffuse"],
              ["b", "Bump"],
              ["s", "Specular"],
              ["r", "Roughness"],
              ["z", "Medium"],
              ["n", "Normal"],
              ["t", "Opacity"]]


    mtable = DtbMaterial.mtable
    def config(self):
        bpy.context.scene.octane.ray_epsilon = 0.000010
    def __init__(self):
        if Global.if_octane()==False:
            return
        self.config()
        OctSkin2()
        for obj in Util.myacobjs():
            print(obj.name)
            self.execute(obj)
        Versions.make_camera()

    def eye_wet(self,ROOT,LINK):
        main = ROOT.new(type = 'ShaderNodeOctSpecularMat')
        main.inputs['Opacity'].default_value = 0.25
        main.inputs['Reflection'].default_value = (1.0, 1.0, 1.0, 1.0)
        main.inputs['Transmission Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        out = ROOT.new(type = 'ShaderNodeOutputMaterial')
        out.target = 'octane'
        LINK.new(main.outputs[0],out.inputs[0])


    def execute(self,obj):
        for slot in obj.material_slots:
            ttable = [
                ["d", None],
                ["b",None],
                ["n", None],
                ["s", None],
                ["r", None],
                ["z", None],
                ["t", None], ]
            mat = bpy.data.materials.get(slot.name)
            if mat is None:
                continue
            mban = -1
            for mt in self.mtable:
                if mat.name.startswith("drb_" + mt[0]):
                    mban = mt[1]
                    break

            ROOT = mat.node_tree.nodes
            LINK = mat.node_tree.links
            flg_universe = False
            outmat = ROOT.new(type='ShaderNodeOutputMaterial')
            if mban==8:
                self.eye_wet(ROOT,LINK)
                continue
            if mban==7:
                mainNode = ROOT.new(type='ShaderNodeOctGlossyMat')

            elif mban<=0:
                mainNode = ROOT.new(type='ShaderNodeOctUniversalMat')
                flg_universe = True
            else:
                mainNode = ROOT.new(type='ShaderNodeGroup')
                mainNode.node_tree = bpy.data.node_groups[oct_ngroup3(SKIN)]
            LINK.new(mainNode.outputs['OutMat'], outmat.inputs['Surface'])
            outmat.target = 'octane'
            for nd in ROOT:
                if nd.type=='TEX_IMAGE':
                    for ft in self.ftable:
                        if ('-IMG.' + ft[0] + "-") in nd.name:
                            adr = nd.image.filepath
                            OCTIMG = ROOT.new(type = 'ShaderNodeOctImageTex')
                            OCTIMG.name = mat.name+"-OCT." + ft[0] + "-"
                            img = bpy.data.images.load(filepath=adr)
                            OCTIMG.image = img
                            inputname = ft[1]
                            if flg_universe and inputname=='Diffuse':
                                inputname = 'Albedo color'
                            LINK.new(mainNode.inputs[inputname],OCTIMG.outputs['OutTex'])
                            for tt in ttable:
                                if tt[0]==ft[0]:
                                    tt[1] = OCTIMG
                                    break
                elif nd.type=='BSDF_PRINCIPLED':
                    p_inp = ["Diffuse", "", "Specular","Roughness", "", "", "Alpha"]
                    for pidx,pi in enumerate(p_inp):
                        if pi!="" and nd.inputs.get(pi) is not None:
                            if nd.inputs.get(pi).type=='VALUE' and len(nd.inputs.get(pi).links)==0:
                                dv = nd.inputs.get(pi).default_value
                                pi = self.ftable[pidx][1]
                                if flg_universe and pi=='Diffuse':
                                    pi = 'Albedo color'
                                print(">>>>>>>>>>>>>>>>>>>>",mainNode,mainNode.inputs[pi],mainNode.inputs[pi],mainNode.inputs[pi].type,)
                                mainNode.inputs[pi].default_value = dv

            self.after_execute(ROOT,LINK,ttable,mainNode,mban>-1)
            if mban>0:
                toGroupInputsDefault(mban==7)
            NodeArrange.toNodeArrange(ROOT)

    def after_execute(self,ROOT,LINK,ttable,universe,flg_human):
        afters = ['ShaderNodeOctRGBSpectrumTex','ShaderNodeValue',
                      'ShaderNodeOct2DTransform','ShaderNodeOctUVWProjection']
        for aidx,af in enumerate(afters,flg_human):
            if flg_human==False and aidx<2:
                continue
            n = ROOT.new(type=af)
            if aidx==0:
                n.inputs[0].default_value = (1.0,1.0,1.0,1.0)
                if ttable[1][1] is not None:
                    LINK.new(n.outputs[0],ttable[1][1].inputs['Power'])
                LINK.new(n.outputs[0], universe.inputs['Specular'])
            elif aidx==1:
                n.outputs[0].default_value = 1
                for i in range(3):#d,b,n
                    if ttable[i][1] is not None:
                        LINK.new(n.outputs[0],ttable[i][1].inputs['Gamma'])
            else:
                for tt in ttable:
                    if tt[1] is not None:
                        if aidx==2:
                            arg = 'Transform'
                        else:
                            arg = 'Projection'
                        LINK.new(n.outputs[0],tt[1].inputs[arg])


NGROUP3 = ['oct_skin','oct_eyewet','oct_eyedry']
SKIN = 0
EWET = 1
EDRY = 2

def oct_ngroup3(idx):
    return NGROUP3[idx] + Util.get_dzidx()

class OctSkin2:
    shaders = []
    oct_skin = None
    def __init__(self):
        self.shaders = []
        self.oct_skin = None
        self.makegroup()
        self.exeSkin()
        self.adjust_default()
    def makegroup(self):
        self.oct_skin = bpy.data.node_groups.new(type="ShaderNodeTree", name=oct_ngroup3(SKIN))
        nsc = 'NodeSocketColor'
        self.oct_skin.inputs.new(nsc, 'Diffuse')
        self.oct_skin.inputs.new(nsc, 'Diffuse2')
        self.oct_skin.inputs.new(nsc, 'Specular')
        self.oct_skin.inputs.new(nsc, 'Roughness')
        self.oct_skin.inputs.new(nsc, 'Bump')
        self.oct_skin.inputs.new(nsc, 'Normal')
        self.oct_skin.inputs.new(nsc, 'Opacity')
        self.oct_skin.outputs.new('NodeSocketShader', 'OutMat')
        self.oct_skin.outputs.new('NodeSocketVector', 'Displacement')
    def adjust_default(self):
        scat = self.shaders[3]
        scat.inputs['Absorption Tex'].default_value = (0.1255,0.51,0.55,1)
        scat.inputs['Scattering Tex'].default_value = (0.51,0.7451,0.902,1)

    def exeSkin(self):
        generatenames = ['NodeGroupInput','ShaderNodeOctDiffuseMat','ShaderNodeOctGlossyMat','ShaderNodeOctScatteringMedium',
                         'ShaderNodeOctMixMat','ShaderNodeOctRoundEdges','ShaderNodeOctRGBSpectrumTex','NodeGroupOutput',]

        con_nums = [
            #Diffuse1
            [[0,0],[1,'Transmission']],
            # Diffuse2
            [[0,1],[1,0]],
            [[1,0],[4,1]],
            [[0,1],[2,0]],
            [[2,0],[4,2]],

            #Roughness
            [[0, 3], [1, 1]],
            [[0,3],[2,2]],

            #Specular
            [[0,2],[2,1]],

            #Normal
            [[0,5],[2,'Normal']],
            [[0, 5], [1, 'Normal']],

             #Scatter1
            [[3,0],[1,'Medium']],

            #Alpha
            [[0,6],[6,0]],
            [[6, 0], [1, 'Opacity']],
            [[6, 0], [2, 'Opacity']],

            #Bump
            [[0, 4], [2, 'Bump']],
            [[0, 4], [1, 'Bump']],

            #RoundEdge
            [[5, 0], [2, 'Edges rounding']],
            [[5, 0], [1, 'Edges rounding']],

              #out
            [[4, 0], [7, 0]],
        ]
        ROOT = self.oct_skin.nodes
        LINK = self.oct_skin.links
        old_gname = ""
        for gidx,gname in enumerate(generatenames):
            if gname=='':
                gname = old_gname
            a = gname.find('.')
            sub = None
            if a>0:
                sub = gname[a+1:]
                gname = gname[:a]
            n = ROOT.new(type=gname)
            n.name = gname + "-" + str(gidx)
            if sub is not None:
                n.blend_type = sub
            self.shaders.append(n)
            print(n.name)
            old_gname = gname
        for cidx,cn in enumerate(con_nums):
            outp = cn[0]
            inp = cn[1]
            print(cidx, outp, inp)
            LINK.new(
                self.shaders[outp[0]].outputs[outp[1]],
                self.shaders[inp[0]].inputs[inp[1]]
            )
        NodeArrange.toNodeArrange(self.oct_skin.nodes)

def getGroupNode(key):
    for slot in Global.getBody().material_slots:
        ROOT = bpy.data.materials[slot.name].node_tree.nodes
        for n in ROOT:
            if n.type=='GROUP':
                if n.node_tree.name.startswith(key):
                    return n

def toGroupInputsDefault(flg_eye):
    if Global.getBody() is None:
        return;
    k3 = [EDRY, EWET, SKIN]
    for kidx, k in enumerate(k3):
        dist_n = getGroupNode(ngroup3(k))
        if dist_n is None:
            continue
        for mat in bpy.data.materials:
            if mat.node_tree is None:
                continue
            n = None
            for sch_n in mat.node_tree.nodes:
                if sch_n.type!='GROUP':
                    continue
                if ('Output' in sch_n.name) or ('Input' in sch_n.name):
                    continue
                if sch_n.node_tree is None:
                    continue
                if sch_n.node_tree.name==dist_n.node_tree.name:
                    n = sch_n
                    break
            if n is None:
                continue
            if flg_eye and ('eye' in sch_n.node_tree.name):
                if ('dry' in sch_n.node_tree.name):
                    for i, inp in enumerate(sch_n.inputs):
                        if len(inp.links) > 0:
                            continue
                        if i == 2:
                            inp.default_value = (0.5, 0.5, 1, 1)
                        else:
                            inp.default_value = (0.6, 0.6, 0.6, 1)
                elif ('wet' in sch_n.node_tree.name):
                    for i, inp in enumerate(sch_n.inputs):
                        if len(inp.links) > 0:
                            continue
                        inp.default_value = (1.0,1.0,1.0,1.0)
            elif ('skin' in sch_n.node_tree.name):
                for i, inp in enumerate(sch_n.inputs):
                    if len(inp.links) > 0:
                        continue
                    if i <2:
                        inp.default_value = (0.7, 0.6, 0.5, 1)
                    elif i < 5:
                        inp.default_value = (0.6, 0.6, 0.6, 1)
                    elif i == 5:
                        inp.default_value = (0.5, 0.5, 1, 1)
                    elif i == 6:
                        inp.default_value = (1.0,1.0,1.0,1.0)

                    mname = mat.name.lower()
                    if ('mouth' in mname) or ('teeth' in mname) or ('nail' in mname):
                        if i>1 and i < 5:
                            inp.default_value = (0.8, 0.8, 0.8, 1)

class OctSkin:
    shaders = []
    oct_skin = None
    def __init__(self):
        self.shaders = []
        self.mcy_skin = None
        self.makegroup()
        self.exeSkin()
    def makegroup(self):
        self.mcy_skin = bpy.data.node_groups.new(type="ShaderNodeTree", name=oct_ngroup3(SKIN))
        nsc = 'NodeSocketColor'
        self.mcy_skin.inputs.new(nsc, 'Albedo color')
        #self.mcy_skin.inputs.new(nsc, 'Diffuse')
        self.mcy_skin.inputs.new(nsc, 'Specular')
        self.mcy_skin.inputs.new(nsc, 'Roughness')
        self.mcy_skin.inputs.new(nsc, 'Bump')
        self.mcy_skin.inputs.new(nsc, 'Normal')
        self.mcy_skin.inputs.new(nsc, 'Opacity')
        #self.mcy_skin.inputs.new(nsc, 'Displacement')
        self.mcy_skin.inputs.new(nsc,"SSSBlue")
        self.mcy_skin.inputs.new(nsc,"SSSRed")
        self.mcy_skin.inputs.new('NodeSocketFloat', 'SSSMix')
        self.mcy_skin.outputs.new('NodeSocketShader', 'OutMat')
        self.mcy_skin.outputs.new('NodeSocketVector', 'Displacement')

    def exeSkin(self):
        generatenames = ['NodeGroupInput','ShaderNodeOctColorCorrectTex','','ShaderNodeOctDiffuseMat',#0
                         'ShaderNodeOctMixMat','','','ShaderNodeOctDisplacementTex',                    #4
                        'ShaderNodeOctScatteringMedium','','','NodeGroupOutput',              #8
                         'ShaderNodeOctSpecularMat','']                                      #12

        con_nums = [
            #Diffuse
            [[0,0],[3,0]],
            [[3, 0], [4, 2]],
            [[4,0],[5,2]],
            [[5,0],[6,2]],

             #Scatter1
            [[8,0],[3,'Medium']],
            #Scatter2
            [[0, 0], [9,7]],
            [[9,0],[12,'Medium']],
            [[12,0],[4,1]],
             #Scatter3
            [[0,0],[10,7]],
            [[10,0],[13,'Medium']],
            [[13,0],[6,1]],
             #Displacement
            [[0,3],[7,'Texture']],
            [[7,0],[6,3]],

              #Normal
            [[0,4],[12,'Normal']],
            [[0, 4], [13, 'Normal']],
            [[0, 4], [3, 'Normal']],

              #Specular
            [[0, 1], [12, 0]],
            [[0, 1], [13, 0]],

              #Rougness
            [[0,2],[12,2]],
            [[0, 2], [13, 2]],
            [[0,2],[3,1]],
              #out
            [[6, 0], [11, 0]],
        ]
        ROOT = self.mcy_skin.nodes
        LINK = self.mcy_skin.links
        old_gname = ""
        for gidx,gname in enumerate(generatenames):
            if gname=='':
                gname = old_gname
            a = gname.find('.')
            sub = None
            if a>0:
                sub = gname[a+1:]
                gname = gname[:a]
            n = ROOT.new(type=gname)
            n.name = gname + "-" + str(gidx)
            if sub is not None:
                n.blend_type = sub
            self.shaders.append(n)
            old_gname = gname
        for cidx,cn in enumerate(con_nums):
            outp = cn[0]
            inp = cn[1]
            LINK.new(
                self.shaders[outp[0]].outputs[outp[1]],
                self.shaders[inp[0]].inputs[inp[1]]
            )
        NodeArrange.toNodeArrange(self.mcy_skin.nodes)

