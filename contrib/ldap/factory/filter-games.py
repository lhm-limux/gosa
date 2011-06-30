# -*- coding: utf-8 -*-

def copyAttr(obj, dst, src, target):
    return {target: getattr(obj, src)}

def mkunixpasswd(obj, dst):
    return {"userPassword": "{%s}%s" % (obj.PasswordMethod, obj.Password)}

def mksmbpasswd(obj, dst):
    return {"sambaLMPasswd": "asdfasdfasdfasdf:asdfasdfasdfasdf",
            "sambaNTPasswd": "asdfdfghdfghdfgh:xcvbxcvbxcvbxcvb"}


#---------------------------------------

fltr1 = """
dst.update(copyAttr(obj, dst, key, 'userPassword'))
"""

fltr2 = """
dst.update(mkunixpasswd(obj, dst))
dst.update(mksmbpasswd(obj, dst))
"""

#---------------------------------------




class klass(object):
    PasswordMethod = "MD5"
    Password = "secret"

obj = klass()
key = "Password"
dst = {}
exec fltr1
print dst
