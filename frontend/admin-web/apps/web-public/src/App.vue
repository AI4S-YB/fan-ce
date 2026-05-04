<script setup lang="ts">
</script>
<template>
  <div id="public-portal">
    <el-menu mode="horizontal" :router="true" style="padding:0 24px;">
      <el-menu-item index="/">
        <span style="font-size:18px;font-weight:700;">Rose Database</span>
      </el-menu-item>
      <div style="flex:1;" />
      <el-menu-item index="/expression">Expression</el-menu-item>
      <el-menu-item index="/genotype">Genotype</el-menu-item>
      <el-menu-item index="/germplasm">Germplasm</el-menu-item>
      <el-menu-item index="/phenotype">Phenotype</el-menu-item>
    </el-menu>
    <main style="max-width:1200px;margin:0 auto;padding:24px;min-height:80vh;">
      <router-view />
    </main>
    <footer style="border-top:1px solid #e5e5e5;padding:16px;text-align:center;color:#999;font-size:12px;">
      China Agricultural University — Rose Database &copy; 2024-2026
    </footer>
  </div>
</template>

<style>
body { margin: 0; font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; }
#public-portal a { color: #606266; text-decoration: none; }
#public-portal a:hover { color: #409eff; }
#public-portal .router-link-active { color: #409eff; font-weight: 600; }
</style>
