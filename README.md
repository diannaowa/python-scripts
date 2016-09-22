# python-scripts

haproxy.py

这是从ansible haproxy module 的代码精简过来的，通过连接到haproxy到sock文件，执行相关到指令，UP/DOWN指定的backend,可以卡看backend的状态

我的haproxy大致：
'''
  frontend services
          bind *:8080

          default_backend web


  backend web
          option httpchk HEAD / HTTP/1.1\r\nHost:\ 192.168.33.20
          server web1 192.168.33.20:80 check inter 2000 fall 3 rise
'''
