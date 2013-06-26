
import os

def getenv(key):
	ret = os.environ.get(key)
	if ret is None:
		raise NameError("Env var %s not set" % key)
	else:
		return ret

def getenv_warn(key, default):
	ret = os.environ.get(key)
	if ret is None:
		print "WARNING: Env var", key, "not set; using default of", default
		return default
	else:
		return ret

# Note: This is used by the config script
def reg_tile_triangular_size(Ni, Nc):
	tile_size = 4
	float_size = 4
	ts = tile_size
	return Ni/ts * (Ni/ts + 1) / 2 * ts*ts * Nc * float_size * 2

