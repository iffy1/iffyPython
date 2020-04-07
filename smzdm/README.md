### 这是什么  
配置关键词，自动每隔N秒到smzdm去爬取需要关键词匹配的商品，然后发到邮件中。  

### 怎么使用  
下载已经编译好windows 64位的可执行文件  
下载地址：  
链接：https://pan.baidu.com/s/1-RnTNRzQHREzmCvgYTxgHQ   
提取码：b01h   

### 如何配置  
打开config.ini文件 按提示，配置SMTP服务器信息，接受邮件的email, 关键词，还有爬取间隔时间  
爬取间隔时间建议不要低于1分钟，防止被服务器block  
运行spider.exe即可  

### 关于源代码  
编写语言：python3  
使用方式：  
1.pip安装requests,configparser以及其他所需的依赖包  
2.打开config.ini文件 按提示，配置SMTP服务器信息，接受邮件的email, 关键词，还有爬取间隔时间  
3.代码主入口是spider.py    

### 声明  
本程序不得使用于商业目的，仅限于代码交流。本人不对程序使用过程中造成的任何问题负责。  

