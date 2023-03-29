import os
import sys
import time
working_dir = os.getcwd()

name0 = 'news_recommend'

service_config = f"""[Unit]
Description= news_recommend
After=network.target

[Service]  
User=root
Group=root
WorkingDirectory={working_dir}
Environment="PATH={sys.prefix}/bin"
ExecStart={sys.executable}/bin/gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
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