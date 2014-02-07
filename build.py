#!python -u

# Copyright (c) Citrix Systems Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, 
# with or without modification, are permitted provided 
# that the following conditions are met:
#
# *   Redistributions of source code must retain the above 
#     copyright notice, this list of conditions and the 
#     following disclaimer.
# *   Redistributions in binary form must reproduce the above 
#     copyright notice, this list of conditions and the 
#     following disclaimer in the documentation and/or other 
#     materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, 
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING 
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF 
# SUCH DAMAGE.

import os, sys
import datetime
import glob
import shutil
import subprocess
import urllib.request
import tarfile
import manifestlatest
import manifestspecific
import re
import errno

def unpack_from_jenkins(filelist, packdir):
    if ('GIT_COMMIT' in os.environ):
        print ("Installer Build ",os.environ["GIT_COMMIT"])
    for urlkey in filelist:
        url = filelist[urlkey]
        print(url)
        fo = urllib.request.urlopen(url)
        tf = tarfile.open(name=None, mode='r|', fileobj=fo)
        tf.extractall(packdir)


header = "verinfo.wxi"
include ="include"

signtool=os.environ['KIT']+"\\bin\\x86\\signtool.exe"
timestamp="http://timestamp.verisign.com/scripts/timestamp.dll"

#remembersignname = "Citrix Systems, Inc"

def sign(filename, signname, additionalcert=None, signstr=None):
    if signstr == None:
        if additionalcert == None:
            callfn([signtool, "sign", "/a", "/s", "my", "/n", signname, "/t", timestamp, filename])
        else:
            callfn([signtool, "sign", "/a", "/s", "my", "/n", signname, "/t", timestamp, "/ac", "c:\\MSCV-VSClass3.cer", filename])
    else:
        callfn(signstr+" "+filename)


def signdrivers(pack, signname, arch, additionalcert, signstr=None):

    additionalcertfiles = [
        pack+"\\xenvif\\"+arch+"\\xenvif.sys",
        pack+"\\xenvbd\\"+arch+"\\xenvbd.sys", 
        pack+"\\xenvbd\\"+arch+"\\xencrsh.sys",
        pack+"\\xennet\\"+arch+"\\xennet.sys",
        pack+"\\xeniface\\"+arch+"\\xeniface.sys",
        pack+"\\xeniface\\"+arch+"\\liteagent.exe",
        pack+"\\xenbus\\"+arch+"\\xenbus.sys",
        pack+"\\xenbus\\"+arch+"\\xen.sys",
        pack+"\\xenbus\\"+arch+"\\xenfilt.sys"
    ]
    
    noadditionalcertfiles = [
        pack+"\\xenvif\\"+arch+"\\xenvif_coinst.dll",
        pack+"\\xenvss\\"+arch+"\\vssclient.dll", 
        pack+"\\xenvss\\"+arch+"\\vsstest.exe", 
        pack+"\\xenvss\\"+arch+"\\xenvss.dll", 
        pack+"\\xenvbd\\"+arch+"\\xenvbd_coinst.dll",
        pack+"\\xennet\\"+arch+"\\xennet_coinst.dll",
        pack+"\\xenbus\\"+arch+"\\xenbus_coinst.dll",
        pack+"\\xenguestagent\\xenguestagent\\xenguestagent.exe",
        pack+"\\xenguestagent\\xenguestagent\\xenguestlib.dll", 
        pack+"\\xenguestagent\\xendpriv\\xendpriv.exe"
    ]


    for afile in additionalcertfiles:
        sign(afile, signname, additionalcert, signstr=signstr)

    for afile in noadditionalcertfiles:
        sign(afile, signname, signstr=signstr)




def signcatfiles(pack, signname, arch, additionalcert, signstr = None):
    catfiles = [
        pack+"\\xenvif\\"+arch+"\\xenvif.cat",
        pack+"\\xenvbd\\"+arch+"\\xenvbd.cat",
        pack+"\\xennet\\"+arch+"\\xennet.cat",
        pack+"\\xeniface\\"+arch+"\\xeniface.cat",
        pack+"\\xenbus\\"+arch+"\\xenbus.cat"
    ]
    
    for afile in catfiles:
        sign(afile, signname, additionalcert, signstr=signstr)


def make_header():
    now = datetime.datetime.now()

    if not(os.path.lexists(include)):
        os.mkdir(include)

    file = open(include+"\\"+header, 'w')
    file.write("<?xml version='1.0' ?>\n");
    file.write("<Include xmlns = 'http://schemas.microsoft.com/wix/2006/wi'>\n")

    file.write("<?define BRANDING_MAJOR_VERSION_STR =\t\""+os.environ['MAJOR_VERSION']+"\"?>\n")
    file.write("<?define BRANDING_MINOR_VERSION_STR =\t\""+os.environ['MINOR_VERSION']+"\"?>\n")
    file.write("<?define BRANDING_MICRO_VERSION_STR =\t\""+os.environ['MICRO_VERSION']+"\"?>\n")
    file.write("<?define BRANDING_BUILD_NR_STR =\t\""+os.environ['BUILD_NUMBER']+"\"?>\n")
    file.write("<?define TOOLS_HOTFIX_NR_STR =\t\""+os.environ['TOOLS_HOTFIX_NUMBER']+"\"?>\n")
    file.write("</Include>")
    file.close();

def callfnout(cmd):
    print(cmd)

    sub = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output = sub.communicate()[0]
    ret = sub.returncode

    if ret != 0:
        raise(Exception("Error %d in : %s" % (ret, cmd)))
    print("------------------------------------------------------------")
    return output.decode('utf-8')


def callfn(cmd):
    print(cmd)
    ret = subprocess.call(cmd)
    if ret != 0:
        raise(Exception("Error %d in : %s" % (ret, cmd)))
    print("------------------------------------------------------------")

def make_pe(pack):
        if os.path.exists('installer\\pe'):
                shutil.rmtree('installer\\pe')
        os.makedirs('installer\\pe')
        shutil.copytree(pack+"\\xenvif", "installer\\pe\\xenvif")
        shutil.copytree(pack+"\\xenvbd", "installer\\pe\\xenvbd")
        shutil.copytree(pack+"\\xennet", "installer\\pe\\xennet")
        shutil.copytree(pack+"\\xenbus", "installer\\pe\\xenbus")
        shutil.copytree("src\\pescripts", "installer\\pe\\scripts")

def make_installers(pack):
    src = ".\\src\\drivers"

    wix=lambda f: os.environ['WIX']+"bin\\"+f
    bitmaps = ".\\src\\bitmaps"
    
    callfn([wix("candle.exe"),src+"\\drivers.wxs","-arch","x64","-darch=x64","-ext","WixDifxAppExtension.dll", "-o", "installer\\driversx64.wixobj"])
    callfn([wix("light.exe"), "installer\\driversx64.wixobj","-darch=x64",wix("difxapp_x64.wixlib"),"-ext","WixUtilExtension.dll","-ext","WixDifxAppExtension.dll","-b",pack,"-o","installer\\driversx64.msm"])
#
    callfn([wix("candle.exe"),src+"\\drivers.wxs","-darch=x86","-ext","WixDifxAppExtension.dll", "-o", "installer\\driversx86.wixobj"])
    callfn([wix("light.exe"), "installer\\driversx86.wixobj","-darch=x86",wix("difxapp_x86.wixlib"),"-ext","WixUtilExtension.dll","-ext","WixDifxAppExtension.dll","-b",pack,"-o","installer\\driversx86.msm"])
#
    callfn([wix("candle.exe"), src+"\\citrixxendrivers.wxs", "-arch","x64", "-darch=x64", "-o", "installer\\citrixxendrivers64.wixobj", "-I"+include, "-dBitmaps="+bitmaps])
    callfn([wix("light.exe"), "installer\\citrixxendrivers64.wixobj", "-darch=x64","-b", ".\\installer", "-o", "installer\\citrixxendriversx64.msi", "-sw1076"])
    if signfiles:
        sign("installer\\citrixxendriversx64.msi", signname, signstr=signstr)
#
    callfn([wix("candle.exe"), src+"\\citrixxendrivers.wxs", "-darch=x86", "-o", "installer\\citrixxendrivers64.wixobj", "-I"+include, "-dBitmaps="+bitmaps])
    callfn([wix("light.exe"), "installer\\citrixxendrivers64.wixobj", "-darch=x86","-b", ".\\installer", "-o", "installer\\citrixxendriversx86.msi", "-sw1076"])
    if signfiles:
        sign("installer\\citrixxendriversx86.msi", signname, signstr=signstr)
#
    src = ".\\src\\vss"
#    
    callfn([wix("candle.exe"), src+"\\citrixvss.wxs", "-arch","x86", "-darch=x86", "-o", "installer\\citrixvssx86.wixobj", "-I"+include, "-dBitmaps="+bitmaps])
    callfn([wix("light.exe"), "installer\\citrixvssx86.wixobj", "-darch=x86", "-b", ".\\installer", "-o", "installer\\citrixvssx86.msi", "-b", pack, "-ext","WixUtilExtension.dll", "-cultures:en-us", "-sw1076"])
    if signfiles:
        sign("installer\\citrixvssx86.msi", signname, signstr=signstr)
#
    callfn([wix("candle.exe"), src+"\\citrixvss.wxs", "-arch","x86", "-darch=x64", "-o", "installer\\citrixvssx64.wixobj", "-I"+include, "-dBitmaps="+bitmaps])
    callfn([wix("light.exe"), "installer\\citrixvssx64.wixobj", "-darch=x64", "-b", ".\\installer", "-o", "installer\\citrixvssx64.msi", "-b", pack, "-ext","WixUtilExtension.dll", "-cultures:en-us", "-sw1076"])
    if signfiles:
        sign("installer\\citrixvssx64.msi", signname, signstr=signstr)
#
    src = ".\\src\\agent"
#

    
    callfn([wix("candle.exe"), src+"\\citrixguestagent.wxs", "-arch","x86", "-darch=x86", "-o", "installer\\citrixguestagentx86.wixobj", "-ext", "WixNetFxExtension.dll", "-I"+include, "-dBitmaps="+bitmaps])
    callfn([wix("light.exe"), "installer\\citrixguestagentx86.wixobj", "-darch=x86", "-b", ".\\installer", "-o", "installer\\citrixguestagentx86.msi", "-b", pack, "-ext", "WixNetFxExtension.dll", "-ext", "WixUiExtension", "-cultures:en-us", "-dWixUILicenseRtf="+src+"\\..\\bitmaps\\EULA_DRIVERS.rtf", "-sw1076"])
    if signfiles:
        sign("installer\\citrixguestagentx86.msi", signname, signstr=signstr)
#
    callfn([wix("candle.exe"), src+"\\citrixguestagent.wxs", "-arch","x64", "-darch=x64", "-o", "installer\\citrixguestagentx64.wixobj", "-ext", "WixNetFxExtension.dll", "-I"+include, "-dBitmaps="+bitmaps])


    callfn([wix("light.exe"), "installer\\citrixguestagentx64.wixobj", "-darch=x64", "-b", ".\\installer", "-o", "installer\\citrixguestagentx64.msi", "-b", pack, "-ext", "WixNetFxExtension.dll", "-ext", "WixUiExtension", "-cultures:en-us", "-dWixUILicenseRtf="+src+"\\..\\bitmaps\\EULA_DRIVERS.rtf", "-sw1076"])
    if signfiles:
        sign("installer\\citrixguestagentx64.msi", signname, signstr=signstr)
    src = ".\\src\\installwizard"
    bitmaps = ".\\src\\bitmaps"
    
    if (all_drivers_signed) :
        use_certs='no'
    else:
        use_certs='yes'
    
    callfn([wix("candle.exe"), src+"\\installwizard.wxs",  "-o", "installer\\installwizard.wixobj", "-ext", "WixUtilExtension", "-ext", "WixUIExtension", "-ext", "WixNetFxExtension.dll", "-I"+include, "-dBitmaps="+bitmaps, "-dusecerts="+use_certs])
    
    # We put a blank file in called XenLegacy.Exe - this doesn't get sucked
    # into the installer, but it is needed to keep light happy (XenLegacy.exe
    # will exentually be sourced from the original build tree)

    f = open("installer\\XenLegacy.Exe","w")
    f.write("DUMMY FILE")
    f.close()
    
    callfn([wix("light.exe"), "installer\\installwizard.wixobj", "-b", ".\\installer", "-o", "installer\\installwizard.msi", "-b", pack, "-ext", "WixUtilExtension", "-ext", "WixNetFxExtension.dll", "-ext", "WixUiExtension", "-cultures:en-us", "-dWixUILicenseRtf="+src+"\\..\\bitmaps\\EULA_DRIVERS.rtf", "-sw1076"])

    if signfiles:
        sign("installer\\installwizard.msi", signname, signstr=signstr)

    # Remove XenLegacy.Exe so that we don't archive the dummy file
    os.remove("installer\\XenLegacy.Exe")    

def archive(filename, files, tgz=False):
    access='w'
    if tgz:
        access='w:gz'
    tar = tarfile.open(filename, access)
    for name in files :
        print('adding '+name)
        tar.add(name)
    tar.close()



def msbuild(name, debug = False):
    cwd = os.getcwd()
    configuration=''
    if debug:
        configuration = 'Debug'
    else:
        configuration = 'Release'

    os.environ['CONFIGURATION'] = configuration

    os.environ['PLATFORM'] = 'Any CPU'

    os.environ['SOLUTION'] = name
    os.environ['TARGET'] = 'Build'

    os.chdir('proj')
    status=shell('msbuild.bat')
    os.chdir(cwd)

def getsrcpath(subproj,debug=False):
    configuration=''
    if debug:
        configuration = 'Debug'
    else:
        configuration = 'Release'
    return  os.sep.join(['proj',subproj,'bin', configuration ])

def copyfiles(name, subproj, dest, debug=False):

    
    src_path = getsrcpath(subproj,debug);

    if not os.path.lexists(name):
        os.mkdir(name)

    dst_path = os.sep.join([dest,name, subproj])

    if not os.path.lexists(dst_path):
        os.makedirs(dst_path)

    for file in glob.glob(os.sep.join([src_path, '*'])):
        print("%s -> %s" % (file, dst_path))
        shutil.copy(file, dst_path)

    sys.stdout.flush()


def shell(command):
    print (command)
    sys.stdout.flush()
    pipe = os.popen(command, 'r', 1)
    for line in pipe:
        print(line.rstrip())

    return pipe.close()

if __name__ == '__main__':

    print (sys.argv)
    
    os.environ['MAJOR_VERSION'] = '6'
    os.environ['MINOR_VERSION'] = '2'
    os.environ['MICRO_VERSION'] = '50'

    os.environ['TOOLS_HOTFIX_NUMBER'] = '20000'
    # Note that the TOOLS_HOTFIX_NUMBER should be reset to 0 following a change of majror, minor or micro numbers

    if 'BUILD_NUMBER' not in os.environ.keys():
        os.environ['BUILD_NUMBER'] = '0'




    if (len(sys.argv) < 3):
        print('.\\build.py <--local|--specific|--latest> <sourcedir> \\')
        print('  [--branch <referencebranch>] \\') 
        print('     [--sign <cert name> [ --addcert <additional certificate>]]')
        print('   | [--signcmd <full command line for signing tool>]')
        sys.exit(1)

    command = sys.argv[1]
    location = sys.argv[2]

    autocommit = False

    signfiles = False
 
    argptr = 3

    additionalcert = None
    signstr = None
    signname = None

    while (len(sys.argv) > argptr):
        if (sys.argv[argptr] == "--branch"):

            reference = sys.argv[argptr+1]
            fo = urllib.request.urlopen('http://www.uk.xensource.com/carbon/'+reference+'/xe-phase-1-latest/xe-phase-1/globals')
            text=str(fo.read())
            m = re.search('PRODUCT_MAJOR_VERSION="(.*?)"',text)
            os.environ['MAJOR_VERSION'] = m.group(1)
            m = re.search('PRODUCT_MINOR_VERSION="(.*?)"',text)
            os.environ['MINOR_VERSION'] = m.group(1)
            m = re.search('PRODUCT_MICRO_VERSION="(.*?)"',text)
            os.environ['MICRO_VERSION'] = m.group(1)
            rtf = open('src\\bitmaps\\EULA_DRIVERS.rtf', "w")
            print(r"{\rtf1\ansi{\fonttbl\f0\fmodern Courier;}\f0\fs10\pard", file=rtf)
            txt = urllib.request.urlopen('http://www.uk.xensource.com/carbon/'+reference+'/xe-phase-1-latest/xe-phase-1/eulas/EULA_DRIVERS_OPEN')
            while (1):
                line = txt.readline()
                if not line:
                    break
                print(str(line, encoding='utf-8')+"\\par", file=rtf)
            print(r"}",file=rtf);
            txt.close()
            rtf.close()
            argptr += 2
            continue

        if (sys.argv[argptr] == "--sign"):
            signfiles = True
            signname = sys.argv[argptr+1]
            argptr += 2
            continue

        if (sys.argv[argptr] == "--addcert"):
            additionalcert = sys.argv[argptr+1]
            argptr += 2
            continue

        if (sys.argv[argptr] == "--signcmd"):
            signcmd = True
            signfiles = True
            signstr = sys.argv[argptr+1]
            additionalcert = ""
            argptr += 2
            continue

    make_header()

    if (command == '--local'):
        print( "Local Build")
        all_drivers_signed = False
    elif (command == '--specific'):
        print( "Specific Build")
        unpack_from_jenkins(manifestspecific.build_tar_source_files, location)
        all_drivers_signed = manifestspecific.all_drivers_signed
    elif (command == '--latest'):
        print ("Latest Build")
        unpack_from_jenkins(manifestlatest.latest_tar_source_files, location)
        all_drivers_signed = manifestlatest.all_drivers_signed
    else:
        print("Unknown command: "+command)
        sys.exit(1)

    if (signfiles):
        signdrivers(location, signname, 'x86', additionalcert, signstr=signstr)
        signdrivers(location, signname, 'x64', additionalcert, signstr=signstr)
        if not all_drivers_signed:
            signcatfiles(location, signname, 'x86', additionalcert, signstr=signstr)
            signcatfiles(location, signname, 'x64', additionalcert, signstr=signstr)

    msbuild('installwizard', False )

    if (signfiles):
        sign(os.sep.join([getsrcpath('installwizard', False),"InstallWizard.exe"]), signname, signstr=signstr)
        sign(os.sep.join([getsrcpath('installgui', False),"InstallGui.exe"]), signname, signstr=signstr)
        sign(os.sep.join([getsrcpath('UIEvent', False),"UIEvent.exe"]), signname, signstr=signstr)
    copyfiles('installwizard', 'installwizard', location, False)
    copyfiles('installwizard', 'installgui', location, False)
    copyfiles('installwizard', 'UIEvent', location, False)
    make_installers(location)

    make_pe(location)

    if 'GIT_COMMIT' in os.environ.keys():
        f = open(os.sep.join(['installer','revision']),"w")
        f.write(os.environ['GIT_COMMIT'])
        print("Revision : "+os.environ['GIT_COMMIT'])
        f.close()

    f = open(os.sep.join(['installer','buildnumber']),"w")
    f.write(os.environ['MAJOR_VERSION']+"."+
            os.environ['MINOR_VERSION']+"."+
            os.environ['MICRO_VERSION']+"."+
            os.environ['BUILD_NUMBER'])
    f.close()
    f = open(os.sep.join(['installer','hotfixnumber']),"w")
    f.write(os.environ['MAJOR_VERSION']+"."+
            os.environ['MINOR_VERSION']+"."+
            os.environ['MICRO_VERSION']+"."+
            os.environ['TOOLS_HOTFIX_NUMBER'])
    f.close()

    listfile = callfnout(['git','ls-tree','-r','--name-only','HEAD'])
    archive('installer\\source.tgz', listfile.splitlines(), tgz=True)
    archive('installer.tar', ['installer'])

    if ('AUTOCOMMIT' in os.environ):
        print ("AUTOCOMMIT = ",os.environ['AUTOCOMMIT'])
        if (os.environ['AUTOCOMMIT'] == "true"):
            repository = os.environ['AUTOREPO']
            shutil.rmtree(os.sep.join([location, 'guest-packages.hg']), True)
            callfn(['hg','clone',repository+"/guest-packages.hg",os.sep.join([location, 'guest-packages.hg'])])
            insturl = open(os.sep.join([location,'guest-packages.hg\\win-tools-iso\\installer.url']),'w')
            print (os.environ['BUILD_URL']+"artifact/installer.tar", file=insturl, end="")
            print (os.environ['BUILD_URL']+"artifact/installer.tar")
            insturl.close()
            pwd = os.getcwd()
            os.chdir(os.sep.join([location, 'guest-packages.hg']))
            callfn(['hg','commit','-m','Auto-update installer to '+os.environ['BUILD_URL']+' '+os.environ['GIT_COMMIT'],'-u','jenkins@xeniface-build'])
            callfn(['hg','push'])
            os.chdir(pwd)
            shutil.rmtree(os.sep.join([location, 'guest-packages.hg']), True)


