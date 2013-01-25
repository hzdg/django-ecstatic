from appconf import AppConf


class EcstaticConf(AppConf):
    BUILD_COMMANDS = []
    COLLECT_BUILT = True
    BUILD_INCLUDES = ['*']
    BUILD_EXCLUDES = ['CVS', '.*', '*~']
