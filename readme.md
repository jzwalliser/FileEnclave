# 简介
这是文件加密工具，可用于加密各式各样的文件。有不少Vibe-coding的成分；其中有30%的代码是元宝写的（在此非常感谢元宝），剩下70%代码是我写的，几乎所有的测试与 Bug 修复工作也由我负责。

# 安装及使用
在目标Linux机上安装python以及相关依赖，然后下载源代码即可运行。
已在 Ubuntu 上完成测试，CLI 所需系统依赖如下：
```bash
sudo apt install 7zip poppler-utils python3-gi-cairo libpango1.0-dev libcairo2-dev fuse libfuse-dev
```
Python 依赖可使用 pip 安装：
```bash
pip install pycairo pdf2image opencv-python fusepy argon2-cffi pillow
```

GUI 的话，还要安装额外的依赖：
```bash
sudo apt install python3-tk xclip
pip install tkinterdnd2 ttkbootstrap pyperclip
```

# 界面
GUI部分的界面是`tkinter`写的，用了`ttkbootstrap`进行美化。

# 内部工作原理&设计
## 原理
1. 向用户请求要加密的文件和密码。
2. 在内部生成随机`salt`，并使用`argon2id`算法（谁让人家安全系数极高呢）对用户密钥进行派生，派生密钥记为`user_password`。
3. 再次在内部生成一个随机密码，记为`file_password`。
4. 创建7z压缩包，用`user_password`将`file_password`加密存储到压缩包中。
5. 给于待加密的文件生成预览图，接着将其切片，推荐的切片大小为`10 MB`。
6. 对于每个切片，使用`file_password`将其加密压缩，预览图同样进行加密压缩。
7. 之后，将切片大小、切片数量、内部`salt`写入`metadata`，放入压缩包中（不进行加密）。
8. 再然后，将文件名、创建访问修改时间，以及其它用户想写入的元数据，一并写入`original_metadata`中，并用`user_password`加密。
9. 当用户想要打开文件的时候，会先解密，然后挂载一个`fuse`文件系统，将解密后的文件呈现给上层应用。
10. 文件并不会一次性全部加载到内存中，而是通过请求读取的偏移量和读取大小，定位到所在切片，再将切片（或多个切片）加载到内存中，最后将数据返回给上层。
11. 可选：用户可以选择是否创建恢复数据；如果创建恢复数据，则将使用`par`给压缩包做恢复，推荐恢复量`15%`。

## 设计考量
1. 7z 容器：7z 压缩包安全性较高，不易受已知明文攻击等影响，因此被选为加密容器格式。
2. `Argon2id` 密钥派生：即便压缩包意外泄露，由于使用了`Argon2id` 进行密钥派生，暴力破解难度极高，即使原密码较弱也能获得较强保护。
3. 双层密码设计：文件加密使用内部随机生成的 `file_password`。当用户需要修改访问密码时，只需重新加密 file_password，无需重新加密全部数据，显著提升效率。
4. FUSE 内存映射：使用`FUSE`文件系统，这样全程数据不落盘，全部存在于内存中，卸载文件系统之后，文件无法恢复；如果这时候电脑突然关机，文件立即被抹去，不发生文件残留在硬盘中、来不及删掉的事故（但是有可能残留在`swap`分区）。
5. 按需加载与缓存：仅加载当前需要读取的数据块，避免打开大文件时触发 OOM。用户可配置缓存大小，将常用切片放入内存，显著提升读取性能。
6. 恢复数据：通过冗余校验提高压缩包对存储介质损坏的容错能力。

# 文件与内部机制详解
## CLI工具
### `creator.py`
用于读取待加密文件，并创建加密压缩包。  
参数：  
- `input`：需要进行加密的文件
- `output`：加密后输出的文件
- `password`：加密密码
- `-c`/`--chunk_size`：分片的块大小，单位是字节，若不填写默认为`2MB`
- `-r`/`--recovery`：设置生成多少比例的冗余恢复数据，取值范围0~100
- `-m`/`--metadata`：添加额外的元数据，需用`JSON`格式传入
- `-y`/`--yes`：开启后直接默认所有交互提问都回答“是”，跳过所有确认提问


### `mounter.py`
用于读取加密压缩包，解密并挂载`fuse`文件系统，向上层提供数据。  
参数：  
- `archive`：需要解密的压缩包
- `password`：解密压缩包用的密码
- `mountpoint`：压缩包解密后挂载到系统的挂载点
- `-f`/`--filename`：默认会从元数据中读取文件名，但可通过本开关指定文件名
- `-c`/`--cachesize`：缓存大小，单位为字节，默认值是`10MB`
- `-o`/`--openfile`：启用后，会在挂载完毕后立即打开目标文件


### `meta_editor.py`
用于修改文件元数据和密码。  
参数：  
- `archive`：你想要编辑的压缩归档文件路径/名称
- `password`：该压缩归档的访问密码
- `data`：你想要修改的目标数据项
- `new`：要修改成的新数据值

### `repair.py`
用于检查并修复损坏文件。  
参数：  
- `-d`/`--directory`：修复指定目录下的所有文件
- `-f`/`--file`：仅修复指定的单个文件

## 自定义库
### `passwordutil.py`
基于argon2id，提供密码派生和随机盐生成。  
函数：  
- `passwordutil.rand(length=32)`：提供16进制随机数字符串，默认长度32位
- `passwordutil.hash(password,salt)`：对密码哈希，须提供盐

### `preview.py`
读取待加密文件，并生成预览图。  
函数：  
- `preview.preview(file_path,quality=100,max_width=960,max_height=540)`：给某个文件生成预览图
## `sevenzipwrapper.py`
基于7z命令行的压缩包处理工具。
函数：
- `read_file(archive,filename,password=None)`：从某个压缩包中读取一个文件
- `write_file(archive,filename,data,password=None)`：想一个压缩包中写入一个文件

## 配置文件
### `config.json`
记录了配置信息。  
字段：  
- `mounter_path`：默认加密压缩包所在路径
- `creator_path`：默认加密文件输出路径
- `rec`：默认恢复量
- `chunk_size`：切片大小
- `tags`：默认标签
- `password`：默认密码
- `default_chunk_size`：默认切片大小

## GUI工具
### `creator_gui.py`
用于生成压缩包，是creator.py的套壳版本。

### `mounter_gui.py`
提供文件预览，整合修复、解密等功能，方便用户操作。

# 致谢
在此，感谢：
1. 各位开发者们写出了超好用的库！  
2. 元宝，帮我写了30%的代码，打下了本项目的基础。  
3. Icons8：提供了精美的图标。
