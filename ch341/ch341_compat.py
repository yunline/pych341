
class CH341DLL:
    prefix=''
    def __init__(self,dll):
        self.dll=dll
    
    def __getattr__(self, name):
        return getattr(self.dll,self.prefix+name)