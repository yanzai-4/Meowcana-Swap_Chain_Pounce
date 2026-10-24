from arduino.app_utils import App, Bridge

from engine import Runner
from nla.flow import default_data_dir, make

print("Meowcana running; saves in %s" % default_data_dir(), flush=True)
App.run(user_loop=Runner(make(), Bridge).step)
