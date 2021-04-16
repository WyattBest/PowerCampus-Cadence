import sys
import main


smtp_config = main.init_config('config_prod.json')
main.main_sync()
