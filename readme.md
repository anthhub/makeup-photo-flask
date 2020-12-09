# 图图 api doc

## base_url

> 以下 api url 以以下的环境作为 base url

- local: http://10.180.9.102:5000/
- online: unknown

### 生成化妆图片

post: /gen_photo

body param:

- photo [file]  图片文件
- target_id [string]  目标图片 id; 当为卡通时, 传 cartoon
