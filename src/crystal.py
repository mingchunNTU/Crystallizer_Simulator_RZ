from data import *
from figure import *
from utility import *
import numpy as np
from scipy.optimize import fsolve

class CSD:
    """
    Module used to represent crystal size distribution
    """

    def __init__(self,size,fraction):
        self.size=size
        self.fraction=fraction
        
class PDF:

    """
    Module used to represent population density function
    """
    def __init__(self,size,density_function):
        self.size=size
        self.density_function=density_function

class crystal:

    def read_setting(self,file):
        tmp1=parameter_read(file)
        self.k=get_variable(tmp1,"shape factor").value[0]
        self.rho=get_variable(tmp1,"crystal density").value[0]
        self.Kr=get_variable(tmp1,"Kr").value[0]
        self.j=get_variable(tmp1,"j").value[0]
        self.i=get_variable(tmp1,"i").value[0]
        self.tau=get_variable(tmp1,"residence time").value[0]
        self.MT=get_variable(tmp1,"slurry concentration").value[0]
        self.R=get_variable(tmp1,"R").value[0]
        self.Lf=get_variable(tmp1,"Lf").value[0]
        self.z=get_variable(tmp1,"z").value[0]
        self.Lp=get_variable(tmp1,"Lp").value[0]

    def nucleation(self,G):
        G_used=G*1e-6/60 # um/min to m/s
        B=self.Kr*(self.MT**self.j)*(G_used**self.i)*1000*1e-18*60 # 1/L*s to 1/um^3*min
        return B
    
    def integral(self,G,tau,L):
        output=-G*tau*(L**3+3*(G*tau)*L**2+6*(G*tau)**2*L+6*(G*tau)**3)*np.exp(-L/G/tau)
        return output
    
    def slurry_concentration(self,G):
        n=self.nucleation(G)/G
        third_moment=0

        C1=n
        third_moment=C1*self.integral(G,self.tau/self.R,self.Lf)-C1*self.integral(G,self.tau/self.R,0)+third_moment

        C2=C1*np.exp(-self.Lf/self.tau/G*(self.R-1))
        third_moment=C2*self.integral(G,self.tau,self.Lp)-C2*self.integral(G,self.tau,self.Lf)+third_moment

        C3=C2*np.exp(-self.Lp/self.tau/G*(1-self.z))
        third_moment=(C3*self.integral(G,self.tau/self.z,10000)-C3*self.integral(G,self.tau/self.z,self.Lp))*self.z+third_moment

        output=third_moment*self.k*self.rho

        return output
    
    def material_balance(self,G):
        output=self.slurry_concentration(G)-self.MT
        return output
    
    def solve(self):
        G=fsolve(self.material_balance,[10])

        self.G=G
        self.B=self.nucleation(G)
        self.n=self.B/G
        self.MT2=self.slurry_concentration(G)
        self.C1=self.n
        self.C2=self.C1*np.exp(-self.Lf/self.tau/self.G*(self.R-1))
        self.C3=self.C2*np.exp(-self.Lp/self.tau/self.G*(1-self.z))

    def output(self,setting_dir,CSD_mesh_size):
        """
        Export the simulation result (PDF and CSD)
        """

        # initialize the size and density function
        size_PDF=variable("size","$\mu m$",[])
        density_function=variable("size","$1/\mu m^4$",[])

        # generate CSD for the first section
        number=int(self.Lf/CSD_mesh_size)+1
        size_section1=array_to_list(np.linspace(0,self.Lf,number))
        size_PDF.value.extend(size_section1)
        
        for i in range(len(size_section1)):
            n=float(self.C1*np.exp(-size_section1[i]*self.R/self.G/self.tau))
            density_function.value.append(n)

        # generate CSD for the second section
        number=int((self.Lp-self.Lf)/CSD_mesh_size)+1
        size_section2=array_to_list(np.linspace(self.Lf,self.Lp,number))
        size_PDF.value.extend(size_section2)
        
        for i in range(len(size_section2)):
            n=float(self.C2*np.exp(-size_section2[i]/self.G/self.tau))
            density_function.value.append(n)

        # generate CSD for the third section
        number=int((15*self.G*self.tau-self.Lp)/CSD_mesh_size)+1
        size_section3=array_to_list(np.linspace(self.Lp,15*self.G*self.tau,number))
        size_PDF.value.extend(size_section3)
        
        for i in range(len(size_section3)):
            n=float(self.C3*np.exp(-size_section3[i]*self.z/self.G/self.tau))*self.z
            density_function.value.append(n)

        self.product_PDF=PDF(size_PDF,density_function)


        # export the PDF
        PDF_output=[self.product_PDF.size,self.product_PDF.density_function]
        variable_output(PDF_output,setting_dir+"Result/PDF.csv")

        # export the CSD
        mesh_size=CSD_mesh_size
        size,number_fraction=DF_to_NF(self.product_PDF.size,self.product_PDF.density_function,mesh_size)
        CSD_output=[size,number_fraction]
        variable_output(CSD_output,setting_dir+"Result/CSD(number).csv")

        size,volume_fraction=NF_to_VF(size,number_fraction)
        CSD_output=[size,volume_fraction]
        variable_output(CSD_output,setting_dir+"Result/CSD(volume).csv")


        # print the simulation result
        tmp1=[]
        tmp1.append("Growth Rate: "+str(self.G)+" um/min")
        tmp1.append("Nucleation Rate: "+str(self.B)+" 1/(um^3*min)")
        tmp1.append("Residence Time: "+str(self.tau)+" min")
        tmp1.append("G*tau: "+str(self.G*self.tau)+" um")
        tmp1.append("MT2: "+str(self.MT2)+" kg/m3")
        print_list(tmp1)
        output_list(tmp1,setting_dir+"Result/report.txt")



