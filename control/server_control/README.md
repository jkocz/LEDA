# Server control

Fabric helper utilities for system admin tasks on the servers.

Helper scripts can be found within `fabfile.py`, but these are run via the command-line
tool `fab`:

```
> fab -l                   list all commands
 
> fab command:args         run command with arguments
```

For example, to install a new package via apt-get:

```
fab apt_install:python-matplotlib
```

Will install matplotlib on all the servers.
