import os
import sys
import time
working_dir = os.getcwd()

name0 = 'son_updater'

service_config = f"""[Unit]
Description= son_updater

[Service]  
User=root
WorkingDirectory={working_dir}
Environment="PATH={sys.prefix}/bin"
ExecStart={sys.executable} {working_dir}/son_updater.py
Restart=always

[Install] 
WantedBy=multi-user.target 
""".replace('\\', '/')

service_file = f"/etc/systemd/system/{name0}.service"
with open(service_file, "w") as f:
    f.write(service_config)
time.sleep(1)
os.system("sudo systemctl daemon-reload")
os.system(f"sudo systemctl start {name0}.service")
os.system(f"sudo systemctl enable {name0}.service")