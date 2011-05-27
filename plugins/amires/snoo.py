import pkg_resources

number = "123"

# Load and initialize resolvers
resolver = {}
for entry in pkg_resources.iter_entry_points("phone.resolver"):
    module = entry.load()
    resolver[module.__name__] = {
            'object': module(),
            'priority': module.priority,
    }

if resolver:
    print "Found these resolvers:"
    print " ".join(resolver.keys())
    print

# Do something with them
res = None
for mod, info in sorted(resolver.iteritems(), key=lambda k: k[1]['priority']):
    res = info['object'].resolve(number)
    if res:
        break

if res:
    print "Resolving number %s to %s." % (number, res)
else:
    print "Number %s not resolved." % number
