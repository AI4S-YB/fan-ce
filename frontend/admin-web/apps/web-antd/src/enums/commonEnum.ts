/**
 * 后端服务请求 前缀
 */
export enum ServicePrefixEnum {
  // 工作流
  ACTIVITI = '/activiti',
  // 基础服务
  BASE = '/base',
  // 文件服务
  FILE = '/base',
  // 网关
  GATEWAY = '/gateway',
  // 代码生成器服务
  GENERATOR = '/generator',
  // 消息服务
  MSG = '/base',
  // 认证服务
  OAUTH = '/oauth',
  // 系统服务
  SYSTEM = '/system',
  // 系统服务
  TENANT = '/system',
}

/**
 * 操作列 类型
 */
export enum ActionEnum {
  // 新增
  ADD = 'add',
  // 复制
  COPY = 'copy',
  // 删除
  DELETE = 'delete',
  // 编辑
  EDIT = 'edit',
  // 详情
  VIEW = 'view',
}

export const VALIDATE_API = {
  [ActionEnum.ADD]: 'Save',
  [ActionEnum.EDIT]: 'Update',
  [ActionEnum.COPY]: 'Save',
};

/**
 * 文件的业务 类型
 */
export enum FileBizTypeEnum {
  // 基础库 文件中心
  BASE_FILE = 'BASE__FILE',
  // 基础库 用户头像
  BASE_USER_AVATAR = 'DEF__USER__AVATAR',
  // 默认库 应用logo
  DEF_APPLICATION_LOGO = 'DEF__APPLICATION__LOGO',
  // 默认库 租户logo
  DEF_TENANT_LOGO = 'DEF__TENANT__LOGO',
  // 扩展库 消息内容附件
  EXTEND_MSG_CONTENT = 'EXTEND__MSG__CONTENT',
}

/**
 * 文件的 桶 （需要提前跟后端约定，并让后端配置到OSS中）
 */
export enum FileBucketEnum {
  // 需要自行在华为云或minio等第三方对象存储提前创建 公开读写的桶
  public = 'tt-public',
}

export enum EnumEnum {
  // authority
  ApplicationAppTypeEnum = 'ApplicationAppTypeEnum',
  AuthorizeType = 'AuthorizeType',
  ComponentEnum = 'ComponentEnum',
  DataScopeType = 'DataScopeType',
  DateType = 'DateType',
  DefGenTestSimpleType2Enum = 'DefGenTestSimpleType2Enum',
  DefGenTestTreeType2Enum = 'DefGenTestTreeType2Enum',
  EntitySuperClassEnum = 'EntitySuperClassEnum',
  FileOverrideStrategyEnum = 'FileOverrideStrategyEnum',
  FileStorageType = 'FileStorageType',
  // file
  FileType = 'FileType',
  GenTypeEnum = 'GenTypeEnum',
  HttpMethod = 'HttpMethod',
  LoginStatusEnum = 'LoginStatusEnum',
  LogType = 'LogType',
  MsgBizType = 'MsgBizType',
  MsgType = 'MsgType',
  PopupTypeEnum = 'PopupTypeEnum',

  // test
  ProductType = 'ProductType',
  ProjectTypeEnum = 'ProjectTypeEnum',
  ProviderType = 'ProviderType',
  SendStatus = 'SendStatus',
  Sex = 'Sex',
  SourceType = 'SourceType',
  SqlConditionEnum = 'SqlConditionEnum',
  SuperClassEnum = 'SuperClassEnum',
  // msg
  TaskStatus = 'TaskStatus',
  TemplateEnum = 'TemplateEnum',
  // tenant
  TenantConnectTypeEnum = 'TenantConnectTypeEnum',

  TenantStatusEnum = 'TenantStatusEnum',
  TenantTypeEnum = 'TenantTypeEnum',
  TplEnum = 'TplEnum',
}
export enum DictEnum {
  APPLICATION_TYPE = 'TENANT_APPLICATION_TYPE',
  AREA_LEVEL = 'GLOBAL_AREA_LEVEL',
  AREA_SOURCE = 'TENANT_AREA_SOURCE',
  CLIENT_TYPE = 'TENANT_CLIENT_TYPE',
  DICT_CLASSIFY = 'TENANT_DICT_CLASSIFY',

  DICT_TYPE = 'TENANT_DICT_TYPE',
  DictionaryType_Global_DATA_TYPE = 'DATA_TYPE',
  DictionaryType_Global_EDUCATION = 'GLOBAL_EDUCATION',
  EchoDictType_Base_INTERFACE_EXEC_MODE = 'INTERFACE_EXEC_MODE',
  EchoDictType_Base_MSG_INTERFACE_LOGGING_STATUS = 'MSG_INTERFACE_LOGGING_STATUS',
  EchoDictType_Base_MSG_TEMPLATE_TYPE = 'MSG_TEMPLATE_TYPE',
  EchoDictType_Base_NOTICE_REMIND_MODE = 'NOTICE_REMIND_MODE',
  EchoDictType_Base_NOTICE_TARGET = 'NOTICE_TARGET',
  EDUCATION = 'GLOBAL_EDUCATION',
  // 全局
  GLOBAL_SEX = 'GLOBAL_SEX',
  NATION = 'GLOBAL_NATION',
  ORG_TYPE = 'BASE_ORG_TYPE',
  PARAMETER_TYPE = 'TENANT_PARAMETER_TYPE',
  // base
  POSITION_STATUS = 'BASE_POSITION_STATUS',
  RESOURCE_DATA_SCOPE = 'TENANT_RESOURCE_DATA_SCOPE',
  RESOURCE_OPEN_WITH = 'TENANT_RESOURCE_OPEN_WITH',
  RESOURCE_TRANSITION_NAME = 'TENANT_RESOURCE_TRANSITION_NAME',
  // tenant
  RESOURCE_TYPE = 'TENANT_RESOURCE_TYPE',
  ROLE_CATEGORY = 'BASE_ROLE_CATEGORY',
  SEX = 'GLOBAL_SEX',

  TENANT_LOGIN_STATUS = 'TENANT_LOGIN_STATUS',
}

export enum MsgTemplateCodeEnum {
  EMAIL_EDIT = 'EMAIL_EDIT',
  MOBILE_EDIT = 'MOBILE_EDIT',
  // 手机登录短信
  MOBILE_LOGIN = 'MOBILE_LOGIN',
  // 注册邮件验证码
  REGISTER_EMAIL = 'REGISTER_EMAIL',
  // 注册短信
  REGISTER_SMS = 'REGISTER_SMS',
}
