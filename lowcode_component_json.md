# 阿里 LowCodeEngine 扩展组件物料协议结构文档

> 来源：[alibaba/lowcode-engine — 物料协议](https://lowcode-engine.cn/site/docs/specs/material-spec) + [资产包协议](https://lowcode-engine.cn/site/docs/specs/assets-spec)

---

## 一、协议层级关系

```
资产包协议 (Assets)
  ├── packages[]         — 各组件的 UMD/CDN 资源信息
  ├── components[]       — 各组件的物料描述（核心）
  │     └── ComponentDescription / RemoteComponentDescription
  ├── sort               — 组件面板 Tab 与分类
  ├── plugins[]          — 设计器插件描述
  ├── setters[]          — 设置器描述
  └── extConfig          — 平台扩展配置
```

一个组件要在低代码引擎中渲染和配置，只需要两类信息：

| 产物 | 内容 | 位置 |
|------|------|------|
| **组件物料描述** | 组件名、分类、可配置属性列表、事件、Snippets | `components[]` |
| **组件资源包** | UMD JS/CSS CDN 地址、全局变量名 | `packages[]` |

---

## 二、资产包顶层结构 (Assets JSON)

```json
{
  "version": "1.1.0",
  "packages": [],
  "components": [],
  "sort": {
    "groupList": ["精选组件", "原子组件"],
    "categoryList": ["通用", "数据展示", "表单", "图表", "工业设备"]
  },
  "plugins": [],
  "setters": [],
  "extConfig": {}
}
```

---

## 三、ComponentDescription — 组件物料描述

每个组件一份 JSON，是该组件的"身份证"。

### 3.1 顶层字段

```typescript
interface ComponentDescription {
  componentName: string;       // 组件名（大写开头，唯一）
  title: string;               // 中文标题
  category: string;            // 所属分类（对应 categoryList 中值）
  icon?: string;               // 组件图标 URL
  description?: string;        // 描述文字
  docUrl?: string;             // 文档链接
  screenshot?: string;         // 截图 URL
  group?: string;              // 分组名 (对应 groupList)
  devMode?: 'proCode' | 'lowCode';  // 开发模式
  npm: {                       // npm 包信息
    package: string;           // npm 包名
    version: string;           // 版本号
    exportName: string;        // 导出名
    destructuring?: boolean;   // 是否解构导入
    main?: string;             // 入口路径
    subName?: string;          // 子组件名
  };
  props: PropConfig[];         // 可配置属性列表（核心）
  snippets: Snippet[];         // 拖入画布时的初始 Schema 片段
  configure?: {                // 高级配置
    component?: ComponentAbility;
    supports?: Supports;
    advanced?: Advanced;
  };
}
```

### 3.2 PropConfig — 属性配置

每个可配置属性描述一份，决定在设计器右侧面板中如何展示。

```typescript
interface PropConfig {
  name: string;                // 属性名 (react props 名)
  title: string | {            // 属性显示标题
    label: string;             // 标题文字
    tip?: string;              // 悬停提示
  };
  propType: PropType;          // 属性类型定义
  setter: string | SetterConfig | (string | SetterConfig)[];  // 设置器
  defaultValue?: any;          // 默认值
  isRequired?: boolean;        // 是否必填
  supportVariable?: boolean;   // 是否支持变量绑定
  display?: 'inline' | 'block' | 'children';  // 显示样式
  condition?: (target: any) => boolean;        // 条件显示
  description?: string;        // 附加说明
  // 分组属性
  type?: 'group';              // 标记为属性分组
  items?: PropConfig[];        // 分组内的子属性
}
```

#### PropType 类型定义

```typescript
type PropType =
  | 'string' | 'number' | 'bool' | 'func' | 'node' | 'element'
  | 'object' | 'array' | 'any'
  | { type: 'oneOf'; value: (string | number)[] }             // 单选枚举
  | { type: 'oneOfType'; value: (string | PropType)[] }       // 多类型联合
  | { type: 'arrayOf'; value: string | PropType }             // 数组元素类型
  | { type: 'shape'; value: Record<string, PropType> };       // 对象 shape
```

### 3.3 SetterConfig — 设置器

```typescript
type SetterConfig = {
  componentName: string;       // 设置器组件名 (如 'NumberSetter')
  props?: Record<string, any>; // 设置器属性
  initialValue?: any;          // 初始值（函数或值）
  defaultValue?: any;          // 默认值
};

// 常用内置设置器：
// StringSetter / NumberSetter / BoolSetter / SelectSetter / ColorSetter
// DateSetter / TimeSetter / JsonSetter / ArraySetter / ObjectSetter
// FunctionSetter / SlotSetter / VariableSetter
```

### 3.4 Snippet — 拖入画布初始 Schema

```typescript
interface Snippet {
  title: string;               // 片段名（组件面板展示）
  screenshot?: string;         // 缩略图
  schema: NodeSchema;          // 拖入时创建的初始节点 Schema
}

interface NodeSchema {
  componentName: string;
  props: Record<string, any>;
  children?: NodeSchema[];
}
```

### 3.5 Supports — 扩展支持声明

```typescript
interface Supports {
  style?: boolean;             // 是否展示样式面板
  className?: boolean;         // 是否展示类名配置
  events?: EventInfo[];        // 支持的事件列表
  loop?: boolean;              // 是否支持循环
  condition?: boolean;         // 是否支持条件渲染
  ref?: boolean;               // 是否支持 ref 绑定
  copy?: boolean;              // 是否可复制
}

interface EventInfo {
  name: string;                // 事件名 (如 'onChange')
  template: string;            // 事件默认代码模板
  description?: string;        // 事件描述
}
```

---

## 四、完整组件物料描述示例（参考 antd Transfer）

```json
{
  "componentName": "Transfer",
  "title": "穿梭框",
  "category": "表单",
  "icon": "https://example.com/icon-transfer.png",
  "npm": {
    "package": "@alifd/next",
    "version": "1.23.0",
    "exportName": "Transfer",
    "destructuring": true
  },
  "props": [
    {
      "name": "dataSource",
      "title": { "label": "数据源", "tip": "数据源数组" },
      "propType": { "type": "arrayOf", "value": "object" },
      "setter": {
        "componentName": "ArraySetter",
        "props": {
          "itemSetter": {
            "componentName": "ObjectSetter",
            "props": {
              "config": {
                "items": [
                  { "name": "key", "title": "key", "setter": "StringSetter" },
                  { "name": "title", "title": "title", "setter": "StringSetter", "isRequired": true }
                ]
              }
            }
          }
        }
      }
    },
    {
      "title": "常用设置",
      "display": "block",
      "type": "group",
      "items": [
        {
          "name": "disabled",
          "title": { "label": "是否禁用" },
          "propType": "bool",
          "setter": "BoolSetter",
          "defaultValue": false
        },
        {
          "name": "showSearch",
          "title": { "label": "是否显示搜索框" },
          "propType": "bool",
          "setter": "BoolSetter",
          "defaultValue": false
        }
      ]
    }
  ],
  "snippets": [
    {
      "title": "穿梭框",
      "schema": {
        "componentName": "Transfer",
        "props": {
          "dataSource": [
            { "key": "1", "title": "内容1" },
            { "key": "2", "title": "内容2" }
          ],
          "showSearch": true
        }
      }
    }
  ],
  "configure": {
    "supports": {
      "style": true,
      "events": [
        {
          "name": "onChange",
          "template": "onChange(targetKeys,direction,moveKeys){\n  console.log('onChange',targetKeys);\n}"
        }
      ]
    }
  }
}
```

---

## 五、Package — 组件资源包描述

```typescript
interface Package {
  id?: string;             // 资源唯一标识
  title?: string;          // 资源标题
  package: string;         // npm 包名
  version: string;         // 版本号
  type?: 'proCode' | 'lowCode';  // 资源类型
  library: string;         // 全局变量名 (window[library] 获取组件实例)
  editUrls?: string[];     // 编辑态 CDN 列表
  urls?: string[];         // 渲染态 CDN 列表
  deps?: string[];         // 依赖的其他资源 ID
  external?: boolean;      // 是否被 external
  async?: boolean;         // 是否异步模块
  exportMode?: 'functionCall'; // 导出方式
  exportSourceId?: string; // 导出来源资源 ID
}
```

### 示例

```json
{
  "title": "Ant Design 组件库",
  "package": "@alifd/next",
  "version": "1.23.18",
  "urls": [
    "https://g.alicdn.com/code/lib/alifd__next/1.23.18/next.min.css",
    "https://g.alicdn.com/code/lib/alifd__next/1.23.18/next-with-locales.min.js"
  ],
  "library": "Next"
}
```

---

## 六、工业设备组件示例 — "主轴监控面板"

基于知识图谱映射，生成一个工业设备专用低代码组件物料描述：

```json
{
  "componentName": "SpindleMonitor",
  "title": "主轴监控面板",
  "category": "工业设备",
  "group": "精选组件",
  "icon": "https://example.com/icons/spindle.png",
  "description": "CNC 数控机床主轴实时监控面板，展示转速、负载、温度等关键参数",
  "devMode": "proCode",
  "npm": {
    "package": "@factory/spindle-monitor",
    "version": "1.0.0",
    "exportName": "SpindleMonitor",
    "destructuring": false
  },
  "props": [
    {
      "title": "基础参数",
      "display": "block",
      "type": "group",
      "items": [
        {
          "name": "spindleSpeed",
          "title": { "label": "主轴转速", "tip": "当前主轴转速 (RPM)" },
          "propType": "number",
          "setter": "NumberSetter",
          "defaultValue": 8000,
          "supportVariable": true
        },
        {
          "name": "spindleLoad",
          "title": { "label": "主轴负载", "tip": "当前主轴负载 (%)" },
          "propType": "number",
          "setter": "NumberSetter",
          "defaultValue": 45.2,
          "supportVariable": true
        },
        {
          "name": "spindleOrientation",
          "title": { "label": "主轴方向", "tip": "主轴当前旋转方向" },
          "propType": { "type": "oneOf", "value": ["clockwise", "counter-clockwise"] },
          "setter": {
            "componentName": "RadioGroupSetter",
            "props": {
              "options": [
                { "title": "顺时针", "value": "clockwise" },
                { "title": "逆时针", "value": "counter-clockwise" }
              ]
            }
          },
          "defaultValue": "clockwise"
        }
      ]
    },
    {
      "title": "操作控制",
      "display": "block",
      "type": "group",
      "items": [
        {
          "name": "autoStart",
          "title": { "label": "自动启动", "tip": "页面加载时自动启动主轴" },
          "propType": "bool",
          "setter": "BoolSetter",
          "defaultValue": false
        },
        {
          "name": "alarmThreshold",
          "title": { "label": "报警阈值 (RPM)", "tip": "超过此转速触发报警" },
          "propType": "number",
          "setter": "NumberSetter",
          "defaultValue": 12000
        }
      ]
    }
  ],
  "snippets": [
    {
      "title": "主轴监控面板（默认）",
      "screenshot": "https://example.com/screenshots/spindle-default.png",
      "schema": {
        "componentName": "SpindleMonitor",
        "props": {
          "spindleSpeed": 8000,
          "spindleLoad": 45.2,
          "spindleOrientation": "clockwise",
          "autoStart": false
        }
      }
    }
  ],
  "configure": {
    "supports": {
      "style": true,
      "className": true,
      "events": [
        {
          "name": "onSpeedChange",
          "template": "onSpeedChange(speed){\n  console.log('Spindle speed changed:', speed);\n}"
        },
        {
          "name": "onAlarm",
          "template": "onAlarm(type, value){\n  console.warn('Alarm:', type, value);\n}"
        }
      ]
    }
  }
}
```

---

## 七、整体资产包完整示例

```json
{
  "version": "1.1.0",
  "packages": [
    {
      "title": "Fusion 基础组件库",
      "package": "@alifd/next",
      "version": "1.23.18",
      "urls": [
        "https://g.alicdn.com/code/lib/alifd__next/1.23.18/next.min.css",
        "https://g.alicdn.com/code/lib/alifd__next/1.23.18/next-with-locales.min.js"
      ],
      "library": "Next"
    },
    {
      "title": "工业设备组件库",
      "package": "@factory/equipment-ui",
      "version": "1.0.0",
      "editUrls": [
        "https://cdn.example.com/factory-equipment/1.0.0/editView.js",
        "https://cdn.example.com/factory-equipment/1.0.0/editView.css"
      ],
      "urls": [
        "https://cdn.example.com/factory-equipment/1.0.0/main.js",
        "https://cdn.example.com/factory-equipment/1.0.0/main.css"
      ],
      "library": "FactoryEquipment"
    }
  ],
  "components": [
    {
      "componentName": "SpindleMonitor",
      "title": "主轴监控面板",
      "category": "工业设备",
      "npm": {
        "package": "@factory/spindle-monitor",
        "version": "1.0.0",
        "exportName": "SpindleMonitor"
      },
      "props": [],
      "snippets": [],
      "configure": { "supports": { "style": true, "events": [] } }
    }
  ],
  "sort": {
    "groupList": ["精选组件", "原子组件", "工业设备"],
    "categoryList": ["通用", "数据展示", "表单", "工业设备"]
  },
  "plugins": [],
  "setters": [],
  "extConfig": {}
}
```

---

## 八、类型总结

```
Assets
├── version: string
├── packages: Array<Package>
│   ├── package, version, library
│   ├── urls[]          (渲染态 CDN)
│   ├── editUrls[]      (编辑态 CDN)
│   └── type: "proCode" | "lowCode"
├── components: Array<ComponentDescription>
│   ├── componentName, title, category
│   ├── npm: { package, version, exportName }
│   ├── props: Array<PropConfig>
│   │   ├── name, title, propType
│   │   ├── setter (StringSetter|NumberSetter|BoolSetter|SelectSetter|...)
│   │   ├── defaultValue, isRequired, supportVariable
│   │   └── type: "group" + items[]  (属性分组)
│   ├── snippets: Array<Snippet>
│   │   ├── title
│   │   └── schema: { componentName, props, children? }
│   └── configure: { supports: { style, className, events[] } }
├── sort: { groupList[], categoryList[] }
├── plugins: Array<PluginDescription>
├── setters: Array<SetterDescription>
└── extConfig: Record<string, any>
```
