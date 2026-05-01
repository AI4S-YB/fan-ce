import type { FileBasicColumn, FileItem, PreviewFileItem } from './typing';

import type { ActionItem, BasicColumn } from '#/components/Table';

import { Progress, Tag } from 'ant-design-vue';

import TableAction from '#/components/Table/src/components/TableAction.vue';
import { $t } from '#/locales';
import { formatFileSize } from '#/utils/file';

import { isImgTypeByName } from './helper';
import ThumbUrl from './ThumbUrl.vue';
import { UploadResultStatus } from './typing';

const t = $t;

// 文件上传列表
export function createTableColumns(): FileBasicColumn[] {
  return [
    {
      dataIndex: 'thumbUrl',
      title: t('component.upload.legend'),
      width: 100,
      customRender: ({ record }) => {
        const { thumbUrl } = (record as FileItem) || {};
        return thumbUrl && <ThumbUrl fileUrl={thumbUrl} />;
      },
    },
    {
      dataIndex: 'name',
      title: t('component.upload.fileName'),
      align: 'left',
      customRender: ({ text, record }) => {
        const { percent, status: uploadStatus } = (record as FileItem) || {};
        let status: 'active' | 'exception' | 'normal' | 'success' = 'normal';
        switch (uploadStatus) {
          case UploadResultStatus.ERROR: {
            status = 'exception';
            break;
          }
          case UploadResultStatus.SUCCESS: {
            {
              status = 'success';
              // No default
            }
            break;
          }
          case UploadResultStatus.UPLOADING: {
            status = 'active';
            break;
          }
        }

        return (
          <div>
            <p class="max-w-70 mb-1 truncate" title={text}>
              {text}
            </p>
            <Progress percent={percent} size="small" status={status} />
          </div>
        );
      },
    },
    {
      dataIndex: 'size',
      title: t('component.upload.fileSize'),
      width: 100,
      customRender: ({ text = 0 }) => {
        return text && formatFileSize(text);
      },
    },
    {
      dataIndex: 'status',
      title: t('component.upload.fileStatue'),
      width: 100,
      customRender: ({ text }) => {
        switch (text) {
          case UploadResultStatus.ERROR: {
            return (
              <Tag color="red">{() => t('component.upload.uploadError')}</Tag>
            );
          }
          case UploadResultStatus.SUCCESS: {
            return (
              <Tag color="green">
                {() => t('component.upload.uploadSuccess')}
              </Tag>
            );
          }
          case UploadResultStatus.UPLOADING: {
            return (
              <Tag color="blue">{() => t('component.upload.uploading')}</Tag>
            );
          }
          // No default
        }

        return text || t('component.upload.pending');
      },
    },
  ];
}
export function createActionColumn(handleRemove: Fn): FileBasicColumn {
  return {
    width: 120,
    title: t('component.upload.operating'),
    dataIndex: 'action',
    fixed: false,
    customRender: ({ record }) => {
      const actions: ActionItem[] = [
        {
          label: t('component.upload.del'),
          danger: true,
          onClick: handleRemove.bind(null, record),
        },
      ];
      return <TableAction actions={actions} outside={true} />;
    },
  };
}
// 文件预览列表
export function createPreviewColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'url',
      title: t('component.upload.legend'),
      width: 100,
      customRender: ({ record }) => {
        const { url } = (record as PreviewFileItem) || {};
        return isImgTypeByName(url) && <ThumbUrl fileUrl={url} />;
      },
    },
    {
      dataIndex: 'name',
      title: t('component.upload.fileName'),
      align: 'left',
    },
  ];
}

export function createPreviewActionColumn({
  handleRemove,
  handleDownload,
}: {
  handleDownload: Fn;
  handleRemove: Fn;
}): BasicColumn {
  return {
    width: 160,
    title: t('component.upload.operating'),
    dataIndex: 'action',
    fixed: false,
    customRender: ({ record }) => {
      const actions: ActionItem[] = [
        {
          label: t('component.upload.del'),
          danger: true,
          onClick: handleRemove.bind(null, record),
        },
        {
          label: t('component.upload.download'),
          onClick: handleDownload.bind(null, record),
        },
      ];

      return <TableAction actions={actions} outside={true} />;
    },
  };
}
