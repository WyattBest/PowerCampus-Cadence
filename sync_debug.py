import sys
import main


smtp_config = main.init_config('config_sample.json')
main.main_sync()
main.de_init()
