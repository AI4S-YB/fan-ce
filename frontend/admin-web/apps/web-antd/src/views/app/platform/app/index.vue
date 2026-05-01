<script setup lang="ts">
import { Page } from '@vben/common-ui';

import { Alert, Card, Descriptions } from 'ant-design-vue';

import { $t } from '@vben/locales';

defineOptions({ name: 'PlatformAppManagementPage' });
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <Card :title="$t('page.appManagement')" :bordered="false">
      <Alert
        class="mb-4"
        :message="$t('page.appManagementReady')"
        :description="$t('page.appManagementDesc')"
        type="success"
        show-icon
      />

      <Descriptions bordered :column="1">
        <Descriptions.Item :label="$t('page.pageUsage')">
          {{ $t('page.pageUsageDesc') }}
        </Descriptions.Item>
        <Descriptions.Item :label="$t('page.currentStatus')">
          {{ $t('page.currentStatusDesc') }}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  </Page>
</template>
