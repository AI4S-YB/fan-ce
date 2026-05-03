<script lang="ts">
import { defineComponent } from 'vue';

import { DocumentEditor } from '@onlyoffice/document-editor-vue';
import { $t } from '@vben/locales';

export default defineComponent({
  name: 'ExampleComponent',
  components: {
    DocumentEditor,
  },
  data() {
    return {
      config: {
        document: {
          fileType: 'docx',
          key: 'BdyjKAvcDYtFManaSWQSZNm4e2ynQod121s',
          title: 'Example Document Title.docx',
          url: 'http://localhost:8001/api/v1/system/file/info',
          permissions: {
            print: true,
            download: true, // 用户是否可以下载
          },
        },

        documentType: 'word',
        editorConfig: {
          mode: 'edit',
          lang: 'zh-cn',
          callbackUrl: 'http://localhost:8001/api/v1/system/file/callback',
        },
      },
    };
  },
  methods: {
    onDocumentReady() {
      console.log('Document is loaded');
    },
    onLoadComponentError(errorCode: any, errorDescription: any) {
      switch (errorCode) {
        case -3: {
          // DocsAPI is not defined
          console.log(errorDescription);
          break;
        }

        case -2: {
          // Error load DocsAPI from http://documentserver/
          console.log(errorDescription);
          break;
        }

        case -1: {
          // Unknown error loading component
          console.log(errorDescription);
          break;
        }
      }
    },
  },
});
</script>

<template>
  <DocumentEditor
    id="docEditor"
    document-server-url="http://localhost:8092"
    :config="config"
    :events_onDocumentReady="onDocumentReady"
    :on-load-component-error="onLoadComponentError"
  />
</template>
