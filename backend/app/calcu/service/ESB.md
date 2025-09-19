ESB文档模板


# <center>[调用方]-[总线]-[接收方]</center>
## <center>xxxxxxxxxxxxxxx接口说明文档</center>
<br/>
### 文档信息表：
<table>
<tr><th colspan="4" style="background-color:#c0d6cb">文档基本信息</th></tr>
<tr><td>项目名称</td><td>精益制造数据集成项目</td></tr>
<tr><td>当前项目阶段</td><td>开发阶段</td></tr>
<tr><td>文档版本</td><td >1.0</td></tr>
<tr><td>文档创建日期</td><td >xxx</td></tr>
<tr><td>当前修订日期</td><td></td></tr>
</table>
<hr/>
<table>
<tr><th colspan="5" style="background-color:#c0d6cb">文档修订信息</th></tr>
<tr><th>版本</th><th>日期</th><th>作者</th><th>变更记录</th></tr>
<tr><td>1.0</td><td>xxxx</td><td>陈鑫</td><td>创建文档</td></tr>
</table>
<hr/>

### 文档概述:

     本文档主要阐述了总线系统集成接收方系统提供的xxxxxxxxxxxxxxx接口，并提供接口服务供调用方系统调用。涵盖了调用方系统调用总线接口的定义，包括请求定义，响应定义，请求响应业务报文样例。
### 阅读对象：
    本文档为接口说明技术文档，阅读对象主要包括：总线系统架构师、总线开发运维人员、调用方系统开发人员,接收方系统开发人员.

### 限定和假设：

1. 对于HTTP协议的请求，报文大小建议在1M以内
2. 总线不进行业务处理，只进行消息路由，日志监控等
3. 接口的实现方式为调用方系统调用实时发送，接收方系统同步接收
4. 调用方系统调用总线接口的时候需要遵循总线的标准规范
5. 调用方系统发送的请求头信息和业务报文信息总线都会原封不动的传递给接收方系统
6. 调用方和接收方都需要记录总线消息头中定义的唯一消息号requestId
7. 业务报文消息内容需调用方系统与接收方系统确认保持一致
8. 总线调用接收方系统的默认超时时间为30s
9. 假设调用方系统与总线、接收方系统与总线之间的网络都已经打通

### 英文缩写：

|名称缩写|描述|
|:----    |:-------|
|总线| EntQMSrise Service Bus|
|调用方| 调用方|
|接收方| 接收方|
|HTTP| Hyper Text Transfer Protocol|

<br>
### 接口业务简要说明：

### 请求URL：
测试地址：` 	http://172.30.9.40:18080/esb/comm/api `

### 请求方式：
- POST 

### Request Header：

|参数名称|是否必填|数据类型|说明|取值|
|:----  |:---|:----- |:-----   |:-----   |
|Content-Type | 是| String |内容格式 | application/json |
|requestId |是  | String | 消息流水号，全局唯一，唯一标识本次请求,UUID字符串 |例：4c2403b5-cf43-48df-a330-9a43ba5b0320 |
|sourceSystem | 是 | String | 客户端业务系统简称|调用方 |
|serviceName | 是 | String | 总线接口服务名称，由总线平台提供| 	服务名称 |
|trackId | 否 | String | 链路追踪号，全局唯一，由发起方生成，同一个调用链路下trackId相同,UUID字符串 | 例：542403b5-1111-2222-a330-7643ba5b0320|
|requestTime | 是 | String | 当前请求发起时间 格式:**yyyy-MM-dd HH:mm:ss** | 例：2021-11-29 18:50:30|

### Request Body：

<font color="#FF0000">如下红色业务字段需要相关业务人员自己确认保持一致：</font>

|字段名称|数据类型|字段长度|是否必填|字段描述|
|:----    |:---|:----- |:-----|-----   |
|<font color="#FF0000">字段</font> | <font color="#FF0000">字段类型</font>  |<font color="#FF0000">字段长度</font>  | <font color="#FF0000">是否必填</font> | <font color="#FF0000">字段含义</font>  |


### 请求报文示例：
```

```
### Response Header：

|参数名称|是否必填|数据类型|说明|取值|
|:----    |:---|:----- |:-----  |:-----   |
|Content-Type | 是 | String | 内容类型 |application/json | 
|statusFlag | 是 | String |ESB上的响应状态，分为1和0 两种状态：1代表成功、0代表失败| 1 | 
|requestId | 是 | String|请求过来的消息流水号，UUID字符串 | 例：4c2403b5-cf43-48df-a330-9a43ba5b0320 | 
|esbCode | 是 | String | 总线上的响应码 |000000 | 
|esbDesc | 是 | String |总线上的响应描述 | successful | 

### Response Body：

<font color="#FF0000">如下红色业务字段需要相关业务人员自己确认保持一致：</font>

|字段名称|数据类型|字段长度|是否必填|字段描述|
|:----    |:---|:----- |:-----|-----   |
|<font color="#FF0000">字段</font> | <font color="#FF0000">字段类型</font>  |<font color="#FF0000">字段长度</font>  | <font color="#FF0000">是否必填</font> | <font color="#FF0000">字段含义</font>  |


###  **响应报文示例：**
```


```
### 客户端调用ESB接口示例代码：

[业务系统调用ESB接口示例代码](http://172.30.9.40/apidoc/web/#/5/24 )

### 响应码：
[响应码说明](http://172.30.9.40/apidoc/web/#/5/23"响应码说明")






ESB文档实例

# <center>[QMS]-[总线]-[TC]</center>
## <center>接收QMS PC表接口说明文档</center>
<br/>
### 文档信息表：
<table>
<tr><th colspan="4" style="background-color:#c0d6cb">文档基本信息</th></tr>
<tr><td>项目名称</td><td>精益制造数据集成项目</td></tr>
<tr><td>当前项目阶段</td><td>开发阶段</td></tr>
<tr><td>文档版本</td><td >1.0</td></tr>
<tr><td>文档创建日期</td><td >2022/01/17</td></tr>
<tr><td>当前修订日期</td><td></td></tr>
</table>
<hr/>
<table>
<tr><th colspan="5" style="background-color:#c0d6cb">文档修订信息</th></tr>
<tr><th>版本</th><th>日期</th><th>作者</th><th>变更记录</th></tr>
<tr><td>1.0</td><td>2022/01/17</td><td>毛欢</td><td>创建文档</td></tr>
<tr><td>1.1</td><td>2022/1/27</td><td>毛欢</td><td>变更文档</td></tr>
</table>
<hr/>

### 文档概述:

     本文档主要阐述了总线系统集成TC系统提供的接收QMS系统PC表接口，并提供接口服务供QMS系统调用。涵盖了QMS系统调用总线接口的定义，包括请求定义，响应定义，请求响应业务报文样例。
### 阅读对象：
    本文档为接口说明技术文档，阅读对象主要包括：总线系统架构师、总线开发运维人员、TC系统开发人员,QMS系统开发人员.

### 限定和假设：

1. 对于HTTP协议的请求，报文大小建议在1M以内
2. 总线不进行业务处理，只进行消息路由，日志监控等
3. 接口的实现方式为QMS系统调用实时发送，TC系统同步接收
4. QMS系统调用总线接口的时候需要遵循总线的标准规范
5. QMS系统发送的请求头信息和业务报文信息总线都会原封不动的传递给TC系统
6. QMS和TC都需要记录总线消息头中定义的唯一消息号requestId
7. 业务报文消息内容需QMS系统与TC系统确认保持一致
8. 总线调用TC系统的默认超时时间为30s
9. 假设QMS系统与总线、TC系统与总线之间的网络都已经打通

### 英文缩写：

|名称缩写|描述|
|:----    |:-------|
|总线| EntQMSrise Service Bus|
|QMS| QMS|
|TC| TC|
|HTTP| Hyper Text Transfer Protocol|

<br>
### 接口业务简要说明：

### 请求URL：
测试地址：`  http://172.30.9.40:18080/esb/comm/api `
*生产环境*：`	http://172.30.9.50/esb/comm/api`

### 请求方式：
- POST 

### Request Header：

|参数名称|是否必填|数据类型|说明|取值|
|:----  |:---|:----- |:-----   |:-----   |
|Content-Type | 是| String |内容格式 | application/json |
|requestId |是  | String | 消息流水号，全局唯一，唯一标识本次请求,UUID字符串 |例：4c2403b5-cf43-48df-a330-9a43ba5b0320 |
|sourceSystem | 是 | String | 客户端业务系统简称|QMS |
|serviceName | 是 | String | 总线接口服务名称，由总线平台提供| S_QMS_PLM_PCtable_S |
|trackId | 否 | String | 链路追踪号，全局唯一，由发起方生成，同一个调用链路下trackId相同,UUID字符串 | 例：542403b5-1111-2222-a330-7643ba5b0320|
|requestTime | 是 | String | 当前请求发起时间 格式:**yyyy-MM-dd HH:mm:ss** | 例：2023-08-09 18:50:30|

### Request Body：

`如下业务字段需要相关业务人员自己确认保持一致：`

![](http://172.30.9.40/apidoc/server/index.php?s=/api/attachment/visitFile/sign/20777c87d250c615fa95b0ec58fec4d7)

![](http://172.30.9.40/apidoc/server/index.php?s=/api/attachment/visitFile/sign/122830947e578de8c3e60bf1f7d1bd58)

![](http://172.30.9.40/apidoc/server/index.php?s=/api/attachment/visitFile/sign/c2471cff9a6744b983f61f342f77f0da)

### 请求报文示例：
```
{
    "CompanyCode": "G001",
    "ProductDefCode": "50040063",
    "PCVersion": "V00",
    "ProductFragment": [{
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-01-020A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-01-0201",
                    "InspectItemName": "出风罩",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "先在网罩与端盖之间涂一圈密封胶，再将网罩端盖紧固，紧固力矩 9.5 N·m，加螺纹锁固剂。\t\t",
                    "Frequency": "",
                    "UnitCode": "N.m",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000074",
                    "InspectInstrumentName": "力矩扳手5-25N·m",
                    "QuantitateStandard": "9.50000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "0.0",
                    "Note": "",
                    "QuantitateLower": "0.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "0",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-01-030A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-01-0301",
                    "InspectItemName": "M10螺栓紧固力矩",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "40N·m",
                    "Frequency": "",
                    "UnitCode": "N.m",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "5024003141",
                    "InspectInstrumentName": "扭力扳手\\20-100N.M",
                    "QuantitateStandard": "40.0000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "0.0",
                    "Note": "",
                    "QuantitateLower": "0.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "0",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-020A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0201",
                    "InspectItemName": "NJ2218轴承加油",
                    "InspectItemClassName": "功能性能",
                    "ReqText": "77.5±2g",
                    "Frequency": "",
                    "UnitCode": "g",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000093",
                    "InspectInstrumentName": "电子称0-15kg",
                    "QuantitateStandard": "77.5000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "2.0",
                    "Note": "",
                    "QuantitateLower": "-2.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "0",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-030A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0301",
                    "InspectItemName": "封环储油室加油",
                    "InspectItemClassName": "功能性能",
                    "ReqText": "封环加油51±2g。\t\t",
                    "Frequency": "",
                    "UnitCode": "g",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000093",
                    "InspectInstrumentName": "电子称0-15kg",
                    "QuantitateStandard": "51.0000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "2.0",
                    "Note": "",
                    "QuantitateLower": "-2.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "0"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-040A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0401",
                    "InspectItemName": "非端轴承室加油",
                    "InspectItemClassName": "功能性能",
                    "ReqText": "在油孔加油检查油路，轴承室加油28.5±2g。\t",
                    "Frequency": "",
                    "UnitCode": "g",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000093",
                    "InspectInstrumentName": "电子称0-15kg",
                    "QuantitateStandard": "28.5000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "2.0",
                    "Note": "",
                    "QuantitateLower": "-2.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "0"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-050A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0501",
                    "InspectItemName": "轴承装配",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "用油压机将轴承外圈压入非传动端端盖轴承室内，压力10KN",
                    "Frequency": "",
                    "UnitCode": "",
                    "InspectInstrumentFlag": "",
                    "InspectInstrumentCode": "",
                    "InspectInstrumentName": "",
                    "QuantitateStandard": "",
                    "Symbol": "",
                    "QuantitateUpper": "",
                    "Note": "",
                    "QuantitateLower": "",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "0"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-060A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0601",
                    "InspectItemName": "四点检测轴承压入深度及平齐度",
                    "InspectItemClassName": "功能性能",
                    "ReqText": "十字四点测量轴承端面到轴承室端面尺寸，要求最大与最小值之差≤0.02mm。\t\t",
                    "Frequency": "",
                    "UnitCode": "mm",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000086",
                    "InspectInstrumentName": "深度尺0-300mm",
                    "QuantitateStandard": "0.0200000000000000",
                    "Symbol": "E",
                    "QuantitateUpper": "",
                    "Note": "",
                    "QuantitateLower": "",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-080A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0801",
                    "InspectItemName": "热套轴承内圈",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "两端轴承内圈加热到110±5℃，确认达到温度后，分别热套于转轴两端。",
                    "Frequency": "",
                    "UnitCode": "℃",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "999-00759",
                    "InspectInstrumentName": "磁感应加热器",
                    "QuantitateStandard": "110.000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "5.0",
                    "Note": "",
                    "QuantitateLower": "-5.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }, {
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0802",
                    "InspectItemName": "测量非端轴承装配尺寸",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "非传动端：十字四点测量轴承内圈到转轴端面尺寸，要求最大与最小值之差≤0.02mm.",
                    "Frequency": "",
                    "UnitCode": "mm",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000086",
                    "InspectInstrumentName": "深度尺0-300mm",
                    "QuantitateStandard": "0.0200000000000000",
                    "Symbol": "E",
                    "QuantitateUpper": "",
                    "Note": "",
                    "QuantitateLower": "",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-090A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-0901",
                    "InspectItemName": "挡圈加热温度",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "80±5℃",
                    "Frequency": "",
                    "UnitCode": "℃",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "999-00759",
                    "InspectInstrumentName": "磁感应加热器",
                    "QuantitateStandard": "80.0000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "5.0",
                    "Note": "",
                    "QuantitateLower": "-5.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-100A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-1001",
                    "InspectItemName": "传动端轴承内圈加热",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "两端轴承内圈加热到110±5℃，确认达到温度后，分别热套于转轴两端。",
                    "Frequency": "",
                    "UnitCode": "℃",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "999-00759",
                    "InspectInstrumentName": "磁感应加热器",
                    "QuantitateStandard": "110.000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "5.0",
                    "Note": "",
                    "QuantitateLower": "-5.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }, {
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-1002",
                    "InspectItemName": "测量传动端轴承装配尺寸",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "传动端：十字四点测量轴承内圈到转轴端面尺寸，要求最大与最小值之差≤0.02mm",
                    "Frequency": "",
                    "UnitCode": "mm",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000086",
                    "InspectInstrumentName": "深度尺0-300mm",
                    "QuantitateStandard": "0.0200000000000000",
                    "Symbol": "E",
                    "QuantitateUpper": "",
                    "Note": "",
                    "QuantitateLower": "",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-110A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-1101",
                    "InspectItemName": "轴承内圈端面到转轴端面的尺寸",
                    "InspectItemClassName": "功能性能",
                    "ReqText": "最大值与最小值之差≤0.02mm",
                    "Frequency": "",
                    "UnitCode": "",
                    "InspectInstrumentFlag": "",
                    "InspectInstrumentCode": "YJGJ000086",
                    "InspectInstrumentName": "深度尺0-300mm",
                    "QuantitateStandard": "",
                    "Symbol": "",
                    "QuantitateUpper": "",
                    "Note": "",
                    "QuantitateLower": "",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-120A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-1201",
                    "InspectItemName": "轴承套加热",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "轴承套加热到80±5℃，(若烘箱加热，加热至120±10℃，保温20min)将轴承放入轴承套内\t\t",
                    "Frequency": "",
                    "UnitCode": "℃",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "999-00759",
                    "InspectInstrumentName": "磁感应加热器",
                    "QuantitateStandard": "80.0000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "5.0",
                    "Note": "",
                    "QuantitateLower": "-5.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }, {
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-1202",
                    "InspectItemName": "轴承套",
                    "InspectItemClassName": "外观",
                    "ReqText": "检查轴承套。要求无毛刺、高点、锈蚀和磕碰伤，用擦拭纸擦拭，擦拭纸上不能留有异物和变色。",
                    "Frequency": "",
                    "UnitCode": "",
                    "InspectInstrumentFlag": "",
                    "InspectInstrumentCode": "",
                    "InspectInstrumentName": "",
                    "QuantitateStandard": "",
                    "Symbol": "",
                    "QuantitateUpper": "",
                    "Note": "",
                    "QuantitateLower": "",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-02-130A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-02-1301",
                    "InspectItemName": "轴承套入深度及平齐度",
                    "InspectItemClassName": "功能性能",
                    "ReqText": "最大值与最小值之差≤0.02mm",
                    "Frequency": "",
                    "UnitCode": "",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000086",
                    "InspectInstrumentName": "深度尺0-300mm",
                    "QuantitateStandard": "",
                    "Symbol": "",
                    "QuantitateUpper": "",
                    "Note": "",
                    "QuantitateLower": "",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-03-050A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-03-0501",
                    "InspectItemName": "非传动端端盖",
                    "InspectItemClassName": "参数方法",
                    "ReqText": "端盖与定子2#、3#位置（抱轴处）使用M12*35（ML40CrMo）螺栓和NL12SP防松垫圈进行紧固，力矩：115N·m。涂锁固剂243；其余端盖与定子紧固位置用M12*35-10.9级螺栓紧固，力矩：115N·m。涂锁固剂243.",
                    "Frequency": "",
                    "UnitCode": "N.m",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "",
                    "InspectInstrumentName": "",
                    "QuantitateStandard": "115.000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "0.0",
                    "Note": "",
                    "QuantitateLower": "0.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }, {
            "CompanyCode": "G001",
            "OwnerCode": "70-1113530445-002-03-060A",
            "QmsOpInspect": [{
                    "CompanyCode": "G001",
                    "InspectItemCode": "70-1113530445-002-03-0601",
                    "InspectItemName": "M12螺栓紧固力矩",
                    "InspectItemClassName": "功能性能",
                    "ReqText": "115N·m",
                    "Frequency": "",
                    "UnitCode": "N.m",
                    "InspectInstrumentFlag": "1",
                    "InspectInstrumentCode": "YJGJ000078",
                    "InspectInstrumentName": "力矩扳手30-340N·m",
                    "QuantitateStandard": "115.000000000000",
                    "Symbol": "F",
                    "QuantitateUpper": "0.0",
                    "Note": "",
                    "QuantitateLower": "0.0",
                    "Defense": "",
                    "selfCheck": "1",
                    "mutualCheck": "1",
                    "specialCheck": "1"
                }
            ]
        }
    ]
}

```
### Response Header：

|参数名称|是否必填|数据类型|说明|取值|
|:----    |:---|:----- |:-----  |:-----   |
|Content-Type | 是 | String | 内容类型 |application/json | 
|statusFlag | 是 | String |ESB上的响应状态，分为1和0 两种状态：1代表成功、0代表失败| 1 | 
|requestId | 是 | String|请求过来的消息流水号，UUID字符串 | 例：4c2403b5-cf43-48df-a330-9a43ba5b0320 | 
|esbCode | 是 | String | 总线上的响应码 |000000 | 
|esbDesc | 是 | String |总线上的响应描述 | successful | 

### Response Body：

`如下业务字段需要相关业务人员自己确认保持一致：`

![](http://172.30.9.40/apidoc/server/index.php?s=/api/attachment/visitFile/sign/c57869a9926c452392ea5529d609d0e0)

###  **响应报文示例：**
```
请求成功：
{
    " MsgType ": S,
    " Msg ": "同步成功1条记录; 更新数据库数据1条;",
" CompanyCode ": G001
" ProductDefCode ": 50040063
}


请求失败：
{
    " MsgType ": E,
    " Msg ": "同步失败1条记录;",
" CompanyCode ": G001
" ProductDefCode ": 50040063
}


```
### 客户端调用ESB接口示例代码：

[业务系统调用ESB接口示例代码](http://172.30.9.40/apidoc/web/#/5/24 )

### 响应码：
[响应码说明](http://172.30.9.40/apidoc/web/#/5/23"响应码说明")








