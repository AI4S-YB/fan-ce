type ColSpanType = number | string;
export interface ColEx {
  style?: any;
  /**
   * raster number of cells to occupy, 0 corresponds to display: none
   * @default none (0)
   * @type ColSpanType
   */
  span?: ColSpanType;

  /**
   * raster order, used in flex layout mode
   * @default 0
   * @type ColSpanType
   */
  order?: ColSpanType;

  /**
   * the layout fill of flex
   * @default none
   * @type ColSpanType
   */
  flex?: ColSpanType;

  /**
   * the number of cells to offset Col from the left
   * @default 0
   * @type ColSpanType
   */
  offset?: ColSpanType;

  /**
   * the number of cells that raster is moved to the right
   * @default 0
   * @type ColSpanType
   */
  push?: ColSpanType;

  /**
   * the number of cells that raster is moved to the left
   * @default 0
   * @type ColSpanType
   */
  pull?: ColSpanType;

  /**
   * <576px and also default setting, could be a span value or an object containing above props
   * @type { span: ColSpanType, offset: ColSpanType } | ColSpanType
   */
  xs?: ColSpanType | { offset: ColSpanType; span: ColSpanType };

  /**
   * ≥576px, could be a span value or an object containing above props
   * @type { span: ColSpanType, offset: ColSpanType } | ColSpanType
   */
  sm?: ColSpanType | { offset: ColSpanType; span: ColSpanType };

  /**
   * ≥768px, could be a span value or an object containing above props
   * @type { span: ColSpanType, offset: ColSpanType } | ColSpanType
   */
  md?: ColSpanType | { offset: ColSpanType; span: ColSpanType };

  /**
   * ≥992px, could be a span value or an object containing above props
   * @type { span: ColSpanType, offset: ColSpanType } | ColSpanType
   */
  lg?: ColSpanType | { offset: ColSpanType; span: ColSpanType };

  /**
   * ≥1200px, could be a span value or an object containing above props
   * @type { span: ColSpanType, offset: ColSpanType } | ColSpanType
   */
  xl?: ColSpanType | { offset: ColSpanType; span: ColSpanType };

  /**
   * ≥1600px, could be a span value or an object containing above props
   * @type { span: ColSpanType, offset: ColSpanType } | ColSpanType
   */
  xxl?: ColSpanType | { offset: ColSpanType; span: ColSpanType };
}

export type ComponentType =
  | 'ApiCascader'
  | 'ApiRadioGroup'
  | 'ApiSelect'
  | 'ApiTransfer'
  | 'ApiTree'
  | 'ApiTreeSelect'
  | 'AutoComplete'
  | 'Cascader'
  | 'Checkbox'
  | 'CheckboxGroup'
  | 'CronTab'
  | 'DatePicker'
  | 'Divider'
  | 'Editor'
  | 'FileUpload'
  | 'IconPicker'
  | 'ImageUpload'
  | 'Input'
  | 'InputCountDown'
  | 'InputGroup'
  | 'InputNumber'
  | 'InputPassword'
  | 'InputSearch'
  | 'InputTextArea'
  | 'MonthPicker'
  | 'RadioButtonGroup'
  | 'RadioGroup'
  | 'RangePicker'
  | 'Rate'
  | 'Render'
  | 'Select'
  | 'Slider'
  | 'StrengthMeter'
  | 'Switch'
  | 'TimePicker'
  | 'TimeRangePicker'
  | 'TreeSelect'
  | 'Upload'
  | 'WeekPicker';
