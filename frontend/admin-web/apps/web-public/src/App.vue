<script setup lang="ts">
</script>
<template>
  <div id="public-portal">
    <header style="border-bottom:1px solid #e5e5e5;padding:12px 24px;display:flex;align-items:center;gap:24px;">
      <router-link to="/" style="font-size:18px;font-weight:700;text-decoration:none;color:#303133;">
        Rose Database
      </router-link>
      <nav style="display:flex;gap:16px;font-size:14px;">
        <router-link to="/expression">Expression</router-link>
        <router-link to="/genotype">Genotype</router-link>
        <router-link to="/germplasm">Germplasm</router-link>
        <router-link to="/phenotype">Phenotype</router-link>
      </nav>
    </header>
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
