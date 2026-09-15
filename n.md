$ sudo systemctl status ssh
Warning: The unit file, source configuration file or drop-ins of ssh.service changed on disk. Run 'systemctl daemon-reload' to reload units.
● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/usr/lib/systemd/system/ssh.service; disabled; preset: enabled)
    Drop-In: /usr/lib/systemd/system/ssh.service.d
             └─ec2-instance-connect.conf
     Active: active (running) since Mon 2026-09-07 20:31:36 UTC; 22h ago
 Invocation: dd8b994ecbd647a99b34ba5351531ed3
TriggeredBy: ● ssh.socket
       Docs: man:sshd(8)
             man:sshd_config(5)
   Main PID: 1018 (sshd)
      Tasks: 1 (limit: 1741)
     Memory: 1.6M (peak: 2.3M)
        CPU: 43ms
     CGroup: /system.slice/ssh.service
             └─1018 "sshd: /usr/sbin/sshd -D -o AuthorizedKeysCommand /usr/share/ec2-instance-connect/eic_run_authorized_keys %u %f -o AuthorizedKeysCom>

Sep 07 20:31:35 ip-172-31-3-93 systemd[1]: Starting ssh.service - OpenBSD Secure Shell server...
Sep 07 20:31:36 ip-172-31-3-93 sshd[1018]: Server listening on 0.0.0.0 port 22.
Sep 07 20:31:36 ip-172-31-3-93 systemd[1]: Started ssh.service - OpenBSD Secure Shell server.
Sep 07 20:31:36 ip-172-31-3-93 sshd[1018]: Server listening on :: port 22.
...skipping...
Warning: The unit file, source configuration file or drop-ins of ssh.service changed on disk. Run 'systemctl daemon-reload' to reload units.
● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/usr/lib/systemd/system/ssh.service; disabled; preset: enabled)
    Drop-In: /usr/lib/systemd/system/ssh.service.d
             └─ec2-instance-connect.conf
     Active: active (running) since Mon 2026-09-07 20:31:36 UTC; 22h ago
 Invocation: dd8b994ecbd647a99b34ba5351531ed3
TriggeredBy: ● ssh.socket
       Docs: man:sshd(8)
             man:sshd_config(5)
   Main PID: 1018 (sshd)
      Tasks: 1 (limit: 1741)
     Memory: 1.6M (peak: 2.3M)
        CPU: 43ms
     CGroup: /system.slice/ssh.service
             └─1018 "sshd: /usr/sbin/sshd -D -o AuthorizedKeysCommand /usr/share/ec2-instance-connect/eic_run_authorized_keys %u %f -o AuthorizedKeysCom>

Sep 07 20:31:35 ip-172-31-3-93 systemd[1]: Starting ssh.service - OpenBSD Secure Shell server...
Sep 07 20:31:36 ip-172-31-3-93 sshd[1018]: Server listening on 0.0.0.0 port 22.
Sep 07 20:31:36 ip-172-31-3-93 systemd[1]: Started ssh.service - OpenBSD Secure Shell server.
Sep 07 20:31:36 ip-172-31-3-93 sshd[1018]: Server listening on :: port 22.
~
~
~
~
~

$ ^C

$ ^C
$ sudo ss -lntp | grep ':22'
LISTEN 0      4096         0.0.0.0:22        0.0.0.0:*    users:(("sshd",pid=1018,fd=3),("systemd",pid=1,fd=182))
LISTEN 0      4096            [::]:22           [::]:*    users:(("sshd",pid=1018,fd=4),("systemd",pid=1,fd=183))
$ 
$ sudo journalctl -u ssh --no-pager -n 50
Sep 07 20:31:35 ip-172-31-3-93 systemd[1]: Starting ssh.service - OpenBSD Secure Shell server...
Sep 07 20:31:36 ip-172-31-3-93 sshd[1018]: Server listening on 0.0.0.0 port 22.
Sep 07 20:31:36 ip-172-31-3-93 systemd[1]: Started ssh.service - OpenBSD Secure Shell server.
Sep 07 20:31:36 ip-172-31-3-93 sshd[1018]: Server listening on :: port 22.
$ 