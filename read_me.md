## pytorch版本EraseNet
该版本的经过作者修改已经完全适用于**手写文字擦除**任务，其中数据集可以从官网下载，mask数据集可以从[link](https://aistudio.baidu.com/aistudio/datasetdetail/122013)该处下载

将训练集、测试集和mask数据集下载到本工程的根目录并解压
> mask数据集解压到训练集的子目录中
解压后文件夹的结构为：
```
|dehw_testA_dataset
    |-images
|dehw_train_dataset
    |-gts
    |-images
    |-mask
```
## 模型训练
```
sh train.sh
```

## 模型重启动训练

在train.sh中将pretrained 选项注释删掉并配置合适的路径

## 模型测试
在test.sh中选择pretrained的路径，并运行
```
sh test.sh
```

在results文件夹中保存含有结果的文件，输出文件
然后添加readme.txt之后保存为zip文件上传即可
