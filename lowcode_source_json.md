# 阿里 LowCodeEngine 搭建协议 JSON 结构文档

> 来源：[alibaba/lowcode-engine — 搭建协议规范](https://lowcode-engine.cn/site/docs/specs/lowcode-spec)

---

## 一、顶层结构

Schema JSON 共包含 14 个一级字段：

```json
{
  "version": "1.0.0",
  "componentsMap": [],
  "componentsTree": [],
  "utils": [],
  "i18n": {},
  "constants": {},
  "css": "",
  "config": {},
  "meta": {},
  "dataSource": {},
  "router": {},
  "pages": []
}
```

| 字段 | 类型 | 级别 | 说明 |
|------|------|:--:|------|
| `version` | String | A | 协议版本号 |
| `componentsMap` | ComponentMap[] | A | 组件名 → npm 包映射关系 |
| `componentsTree` | Array | A | 页面/区块/组件的嵌套组件树（核心） |
| `utils` | Array | - | 工具类扩展映射 |
| `i18n` | Object | AA | 国际化多语言语料 |
| `constants` | Object | - | 应用级全局常量 |
| `css` | String | - | 应用级全局样式 |
| `config` | Object | - | 应用配置（SDK版本/布局/主题） |
| `meta` | Object | - | 业务元数据（名称/作者/时间） |
| `dataSource` | Object | - | 应用级公共数据源 |
| `router` | Object | - | 路由配置 |
| `pages` | Array | - | 多页面索引（S1.1+支持） |

> 规范等级：**A** = 强制实现，**AA** = 推荐实现，**AAA** = 参考实现

---

## 二、`version` — 协议版本号

```json
{
  "version": "1.0.0"
}
```

不同版本号对应不同的渲染 SDK，保障不同版本协议的产物正常渲染。

---

## 三、`componentsMap` — 组件映射关系 [A]

将 schema 中使用的 `componentName` 映射到真实的 npm 包和导出名。

### 单条 ComponentMap 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `componentName` | String | Schema 中使用的组件名，大写字母打头，唯一 |
| `package` | String | npm 公域包名 |
| `version` | String | 包版本号 |
| `destructuring` | Boolean | 是否使用解构方式导入 |
| `exportName` | String | 包导出的实际组件名（与 componentName 不同时填写） |
| `subName` | String | 下标子组件名称（如 `Button.Group`） |
| `main` | String | 包导出组件入口文件路径 |

### 示例

```json
{
  "componentsMap": [
    {
      "componentName": "Button",
      "package": "@alifd/next",
      "version": "1.0.0",
      "destructuring": true
    },
    {
      "componentName": "MySelect",
      "package": "@alifd/next",
      "version": "1.0.0",
      "destructuring": true,
      "exportName": "Select"
    },
    {
      "componentName": "ButtonGroup",
      "package": "@alifd/next",
      "version": "1.0.0",
      "destructuring": true,
      "exportName": "Button",
      "subName": "Group"
    },
    {
      "componentName": "CustomCard",
      "package": "@ali/custom-card",
      "version": "1.0.0"
    },
    {
      "componentName": "CustomInput",
      "package": "@ali/custom",
      "version": "1.0.0",
      "main": "/lib/input",
      "destructuring": true,
      "exportName": "Input"
    }
  ]
}
```

### 出码对应关系

```javascript
// destructuring: true
import { Button } from '@alifd/next';

// destructuring: true, exportName 与 componentName 不同
import { Select as MySelect } from '@alifd/next';

// destructuring: true, 导出子组件
import { Button } from '@alifd/next';
const ButtonGroup = Button.Group;

// destructuring: false（默认导出）
import CustomCard from '@ali/custom-card';

// main 指定路径
import { Input as CustomInput } from '@ali/custom/lib/input';
```

---

## 四、`componentsTree` — 组件树 [A]（核心）

组件树由两种节点类型嵌套构成：

| 节点类型 | `componentName` | 包含内容 |
|----------|:--:|------|
| **容器结构** | `Page` / `Block` / `Component` | 数据源、状态、生命周期、自定义方法、子节点 |
| **组件结构** | `Button` / `Div` / `Table` 等 | 仅 `props` + `children` |

### 4.1 容器结构完整字段

```json
{
  "componentName": "Page",
  "id": "node_oclawu71ac3",
  "fileName": "Page1",
  "props": {},
  "css": "body { font-size: 12px; }",
  "defaultProps": { "name": "xxx" },
  "hidden": false,
  "title": "",
  "isLocked": false,
  "condition": true,
  "conditionGroup": "",
  "state": {
    "text": { "type": "JSExpression", "value": "\"outer\"" }
  },
  "dataSource": {
    "list": [
      {
        "id": "info",
        "isInit": true,
        "type": "fetch",
        "options": {
          "uri": "mock/info.json",
          "method": "GET",
          "params": {},
          "isCors": true,
          "timeout": 5000,
          "headers": {}
        },
        "shouldFetch": {
          "type": "JSFunction",
          "value": "function() { return true; }"
        }
      }
    ]
  },
  "lifeCycles": {
    "componentDidMount": {
      "type": "JSFunction",
      "value": "function componentDidMount() { console.log('did mount'); }"
    },
    "componentWillUnmount": {
      "type": "JSFunction",
      "value": "function componentWillUnmount() { console.log('will unmount'); }"
    }
  },
  "methods": {
    "onClick": {
      "type": "JSFunction",
      "value": "function onClick() { this.setState({ isShowDialog: true }); }"
    },
    "testFunc": {
      "type": "JSFunction",
      "value": "function testFunc() { console.log('test func'); }"
    }
  },
  "originCode": "class LowcodeComponent extends Component { ... }",
  "children": []
}
```

### 4.2 容器结构字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `componentName` | String | `"Page"` / `"Block"` / `"Component"` 三选一 |
| `id` | String | 唯一标识 |
| `fileName` | String | 生成的源文件名 |
| `props` | Object | 公共属性（详见 4.4） |
| `css` | String | 容器私有样式 |
| `defaultProps` | Object | 对外暴露的可配置默认属性 |
| `hidden` | Boolean | 是否隐藏 |
| `title` | String | 标题 |
| `isLocked` | Boolean | 是否在设计器中锁定 |
| `condition` | Boolean | 条件渲染 |
| `conditionGroup` | String | 条件分组 |
| `state` | Object | 组件状态（值为 JSExpression 对象） |
| `dataSource` | Object | 数据源配置（详见 4.3） |
| `lifeCycles` | Object | 生命周期钩子（值为 JSFunction 对象） |
| `methods` | Object | 自定义方法（值为 JSFunction 对象） |
| `originCode` | String | 原始 Class 源码 |
| `children` | Array | 子节点（递归嵌套组件/容器） |

### 4.3 dataSource 数据源结构

```json
{
  "dataSource": {
    "list": [
      {
        "id": "info",
        "isInit": true,
        "type": "fetch",
        "options": {
          "uri": "https://api.example.com/data",
          "method": "GET",
          "params": {},
          "isCors": true,
          "timeout": 5000,
          "headers": {}
        },
        "shouldFetch": {
          "type": "JSFunction",
          "value": "function() { return true; }"
        }
      }
    ],
    "dataHandler": {
      "type": "JSFunction",
      "value": "function(res) { return res.data; }"
    }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `list` | ComponentDataSourceItem[] | 数据请求配置列表 |
| `list[].id` | String | 数据请求唯一标识 |
| `list[].isInit` | Boolean | 是否在组件初始化时自动发送 |
| `list[].type` | String | 请求类型（如 `"fetch"`） |
| `list[].options` | Object | 请求配置（uri/method/params/headers/timeout） |
| `list[].shouldFetch` | JSFunction | 判断是否发送请求的函数 |
| `dataHandler` | JSFunction | 全局数据处理函数（可选） |

### 4.4 Props 属性结构

```json
{
  "props": {
    "id": "my-btn",
    "className": "custom-btn",
    "style": { "width": "100px", "color": "#333" },
    "ref": "myRef",
    "extendProps": {
      "type": "JSExpression",
      "value": "this.props.extraData"
    },

    "text": "点击按钮",
    "size": "large",

    "dataSource": {
      "type": "JSExpression",
      "value": "this.state.list"
    },

    "onClick": {
      "type": "JSFunction",
      "value": "function(e) { console.log(e.target); }"
    }
  }
}
```

#### 系统属性

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String | 组件 ID |
| `className` | String | 样式类名 |
| `style` | Object | 内联样式 |
| `ref` | String | 组件引用名，通过 `this.$(ref)` 获取实例 |
| `extendProps` | 变量绑定 | 继承属性，仅支持变量绑定 |

#### 三种 value 类型

| 类型 | 示例 | 说明 |
|------|------|------|
| **普通 JSON** | `"text": "点击按钮"` | 静态值，直接输出 |
| **JSExpression** | `{ "type": "JSExpression", "value": "this.state.name" }` | JS 表达式，用于变量绑定 |
| **JSFunction** | `{ "type": "JSFunction", "value": "function(e) { ... }" }` | JS 函数体，用于事件绑定 |

---

## 五、`utils` — 工具类扩展映射

```json
{
  "utils": [
    {
      "name": "clone",
      "type": "npm",
      "content": {
        "package": "lodash",
        "version": "0.0.1",
        "exportName": "clone",
        "subName": "",
        "destructuring": false,
        "main": "/lib/clone"
      }
    },
    {
      "name": "moment",
      "type": "npm",
      "content": {
        "package": "@alifd/next",
        "version": "0.0.1",
        "exportName": "Moment",
        "subName": "",
        "destructuring": true,
        "main": ""
      }
    }
  ]
}
```

---

## 六、`i18n` — 国际化语料 [AA]

以语言代码为 key 的多语言文案集合。

```json
{
  "i18n": {
    "zh-CN": {
      "i18n-key1": "你好",
      "i18n-key2": "世界"
    },
    "en-US": {
      "i18n-key1": "Hello",
      "i18n-key2": "World"
    }
  }
}
```

---

## 七、`constants` — 全局常量

```json
{
  "constants": {
    "ENV": "prod",
    "DOMAIN": "xxx.com"
  }
}
```

---

## 八、`css` — 全局样式

```json
{
  "css": "body { font-size: 12px; } .table { width: 100px; }"
}
```

---

## 九、`config` — 应用配置

```json
{
  "config": {
    "sdkVersion": "1.0.3",
    "historyMode": "hash",
    "targetRootID": "J_Container",
    "layout": {
      "componentName": "BasicLayout",
      "props": {
        "logo": "...",
        "name": "测试网站"
      }
    },
    "theme": {
      "package": "@alife/theme-fusion",
      "version": "^0.1.0",
      "primary": "#ff9966"
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| `sdkVersion` | 渲染 SDK 版本 |
| `historyMode` | 路由模式（`"hash"` / `"browser"`） |
| `targetRootID` | 渲染目标 DOM 容器 ID |
| `layout` | 全局布局组件 |
| `theme` | 主题配置（Fusion 用 package，Antd 用 variable） |

---

## 十、`meta` — 应用元数据

```json
{
  "meta": {
    "name": "demo 应用",
    "git_group": "appGroup",
    "project_name": "app_demo",
    "description": "这是一个测试应用",
    "spma": "spa23d",
    "creator": "月飞",
    "gmt_create": "2020-02-11 00:00:00",
    "gmt_modified": "2020-02-11 00:00:00"
  }
}
```

---

## 十一、`dataSource` — 应用级公共数据源

```json
{
  "dataSource": {
    "list": [
      {
        "id": "globalData",
        "isInit": true,
        "type": "fetch",
        "options": {
          "params": {},
          "method": "GET",
          "isCors": true,
          "timeout": 5000,
          "headers": {},
          "uri": "https://api.example.com/global"
        }
      }
    ],
    "dataHandler": {
      "type": "JSFunction",
      "value": "function(res) { return res.data; }"
    }
  }
}
```

---

## 十二、`router` — 路由配置

```json
{
  "router": {
    "baseUrl": "/",
    "historyMode": "hash",
    "routes": [
      { "path": "home", "page": "page1" },
      { "path": "about", "page": "page2" }
    ]
  }
}
```

| 字段 | 说明 |
|------|------|
| `baseUrl` | 路由基础路径 |
| `historyMode` | 路由模式：`"browser"` 或 `"hash"` |
| `routes` | 路由配置列表 |
| `routes[].path` | 路由路径 |
| `routes[].page` | 对应的页面 ID |

---

## 十三、`pages` — 多页面索引

```json
{
  "pages": [
    { "id": "page1", "treeId": "page1" },
    { "id": "page2", "treeId": "page2" }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `id` | 页面唯一标识 |
| `treeId` | 对应 `componentsTree` 中的节点 ID |

---

## 十四、整体架构图

```
project-schema.json
│
├── version        → 协议版本号
├── componentsMap[] → 组件名 → npm 包映射
├── utils[]        → 工具库映射
├── i18n{}         → 多语言文案
├── constants{}    → 全局常量
├── css            → 全局样式
├── config{}       → SDK版本 / 布局 / 主题
├── meta{}         → 业务元数据
├── dataSource{}   → 应用级公共数据源
├── router{}       → 路由配置
├── pages[]        → 多页面索引
│
└── componentsTree[] ─── 【核心】嵌套组件树
    │
    └── [容器节点] componentName: "Page" / "Block" / "Component"
        ├── id, fileName, props, css
        ├── defaultProps      → 对外可配置默认属性
        ├── state             → 组件状态（JSExpression）
        ├── dataSource        → 数据请求配置
        ├── lifeCycles        → 生命周期钩子（JSFunction）
        ├── methods           → 自定义方法（JSFunction）
        │
        └── children: [
            ├── [组件节点] componentName: "Div"
            │   └── children: [
            │       └── [组件节点] componentName: "Button"
            │           └── props: {
            │                静态值: 1234,
            │                变量绑定: { type:"JSExpression", value:"this.state.x" },
            │                事件绑定: { type:"JSFunction", value:"function(e){...}" }
            │              }
            │       ]
            │
            └── [容器节点] componentName: "Block"
                ├── state / dataSource / lifeCycles / methods
                └── children: [ ... ]   ← 继续无限嵌套
            ]
```

---

## 十五、核心设计理念

1. **JSON 即 AST**：`componentsTree` 本质是一棵组件抽象语法树，`type` 字段区分三种 value 类型（静态值 / JSExpression / JSFunction）
2. **三层分离**：**组件结构**（渲染 UI） + **容器结构**（数据/状态/生命周期） + **映射表**（componentName → npm 包）
3. **渐进式搭建**：组件 → 区块（Block）→ 页面（Page）→ 应用（含路由的多页）
4. **声明式行为系统**：事件、数据请求、状态管理全部用 JSON 描述，无需手写 JS 文件
5. **可出码**：每个 Schema 字段都有明确源码转换规则，可生成与手写无差异的 React/Vue/小程序代码
6. **可流通**：基于标准化协议，产物可在不同搭建平台间流通
