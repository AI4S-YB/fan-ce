<script setup lang="ts">
// Component logic can be added here
</script>

<template>
  <div class="app">
    <header class="header">
      <nav class="nav-container">
        <div class="logo">
          <img src="/logo.svg" alt="Logo" />
        </div>
        <div class="nav-links">
          <a href="#" class="nav-link">首页</a>
          <a href="#" class="nav-link">解决方案</a>
          <a href="#" class="nav-link">产品服务</a>
          <a href="#" class="nav-link">关于我们</a>
          <a href="#" class="nav-link">联系我们</a>
        </div>
      </nav>
    </header>

    <router-view />

    <footer class="footer">
      <div class="footer-content">
        <div class="footer-section">
          <h3>联系我们</h3>
          <p>电话：400-123-4567</p>
          <p>邮箱：info@example.com</p>
          <p>地址：北京市朝阳区xxx大厦</p>
        </div>
        <div class="footer-section">
          <h3>关注我们</h3>
          <div class="social-links">
            <a href="#" class="social-link"><i class="fab fa-weixin"></i></a>
            <a href="#" class="social-link"><i class="fab fa-weibo"></i></a>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; 2024 Your Company. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<style>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  position: fixed;
  top: 0;
  z-index: 100;
  width: 100%;
  background-color: white;
  box-shadow: 0 2px 4px rgb(0 0 0 / 10%);
}

.nav-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  padding: 1rem;
  margin: 0 auto;
}

.logo img {
  height: 40px;
}

.nav-links {
  display: flex;
  gap: 2rem;
}

.nav-link {
  font-size: 1.1rem;
  color: #333;
  text-decoration: none;
  transition: color 0.3s ease;
}

.nav-link:hover {
  color: #2563eb;
}

.footer {
  padding: 4rem 2rem 2rem;
  margin-top: auto;
  color: white;
  background-color: #1a365d;
}

.footer-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.footer-section h3 {
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.social-links {
  display: flex;
  gap: 1rem;
}

.social-link {
  font-size: 1.5rem;
  color: white;
  transition: color 0.3s ease;
}

.social-link:hover {
  color: #2563eb;
}

.footer-bottom {
  padding-top: 2rem;
  margin-top: 2rem;
  text-align: center;
  border-top: 1px solid rgb(255 255 255 / 10%);
}

@media (max-width: 768px) {
  .nav-links {
    display: none;
  }
}
</style>
