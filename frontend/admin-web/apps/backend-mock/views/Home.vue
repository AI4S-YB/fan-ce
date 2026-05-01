<script setup lang="ts">
// Component logic can be added here
</script>

<template>
  <div class="home-container">
    <!-- Hero Section -->
    <section class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">数字化转型解决方案</h1>
        <p class="hero-subtitle">为企业提供全方位的数字化转型服务</p>
        <button class="primary-btn">了解更多</button>
      </div>
    </section>

    <!-- Features Section -->
    <section class="features-section">
      <h2 class="section-title">我们的服务</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">
            <i class="fas fa-chart-line"></i>
          </div>
          <h3>数据分析</h3>
          <p>深度挖掘数据价值，助力企业决策</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <i class="fas fa-cloud"></i>
          </div>
          <h3>云服务</h3>
          <p>灵活可扩展的云计算解决方案</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <i class="fas fa-shield-alt"></i>
          </div>
          <h3>安全服务</h3>
          <p>全面的企业级安全防护</p>
        </div>
      </div>
    </section>

    <!-- Solutions Section -->
    <section class="solutions-section">
      <h2 class="section-title">行业解决方案</h2>
      <div class="solutions-grid">
        <div class="solution-card">
          <img src="/images/finance.jpg" alt="金融解决方案" />
          <h3>金融行业</h3>
          <p>为金融机构提供安全、可靠的数字化解决方案</p>
        </div>
        <div class="solution-card">
          <img src="/images/manufacturing.jpg" alt="制造业解决方案" />
          <h3>制造业</h3>
          <p>助力制造企业实现智能化转型</p>
        </div>
        <div class="solution-card">
          <img src="/images/retail.jpg" alt="零售行业解决方案" />
          <h3>零售行业</h3>
          <p>打造全渠道数字化零售体验</p>
        </div>
      </div>
    </section>

    <!-- Contact Section -->
    <section class="contact-section">
      <div class="contact-content">
        <h2>联系我们</h2>
        <p>了解更多详情，请联系我们的专业顾问</p>
        <form class="contact-form">
          <input type="text" placeholder="公司名称" />
          <input type="text" placeholder="联系人" />
          <input type="email" placeholder="电子邮箱" />
          <input type="tel" placeholder="联系电话" />
          <textarea placeholder="咨询内容"></textarea>
          <button type="submit" class="submit-btn">提交</button>
        </form>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.hero-section {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 600px;
  padding: 0 20px;
  color: white;
  text-align: center;
  background: linear-gradient(135deg, #1a365d 0%, #2563eb 100%);
}

.hero-title {
  margin-bottom: 1rem;
  font-size: 3rem;
}

.hero-subtitle {
  margin-bottom: 2rem;
  font-size: 1.5rem;
}

.primary-btn {
  padding: 1rem 2rem;
  font-size: 1.1rem;
  color: #2563eb;
  cursor: pointer;
  background-color: #fff;
  border: none;
  border-radius: 5px;
  transition: all 0.3s ease;
}

.primary-btn:hover {
  background-color: #f3f4f6;
  transform: translateY(-2px);
}

.section-title {
  margin: 4rem 0 2rem;
  font-size: 2.5rem;
  text-align: center;
}

.features-grid,
.solutions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  padding: 2rem;
}

.feature-card,
.solution-card {
  padding: 2rem;
  text-align: center;
  background: white;
  border-radius: 10px;
  box-shadow: 0 4px 6px rgb(0 0 0 / 10%);
  transition: all 0.3s ease;
}

.feature-card:hover,
.solution-card:hover {
  box-shadow: 0 8px 12px rgb(0 0 0 / 15%);
  transform: translateY(-5px);
}

.feature-icon {
  margin-bottom: 1rem;
  font-size: 2.5rem;
  color: #2563eb;
}

.solution-card img {
  width: 100%;
  height: 200px;
  margin-bottom: 1rem;
  object-fit: cover;
  border-radius: 5px;
}

.contact-section {
  padding: 4rem 2rem;
  margin-top: 4rem;
  background-color: #f3f4f6;
}

.contact-content {
  max-width: 600px;
  margin: 0 auto;
  text-align: center;
}

.contact-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2rem;
}

.contact-form input,
.contact-form textarea {
  padding: 1rem;
  font-size: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 5px;
}

.contact-form textarea {
  height: 150px;
  resize: vertical;
}

.submit-btn {
  padding: 1rem;
  font-size: 1.1rem;
  color: white;
  cursor: pointer;
  background-color: #2563eb;
  border: none;
  border-radius: 5px;
  transition: all 0.3s ease;
}

.submit-btn:hover {
  background-color: #1d4ed8;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
  }

  .hero-subtitle {
    font-size: 1.2rem;
  }

  .section-title {
    font-size: 2rem;
  }

  .features-grid,
  .solutions-grid {
    grid-template-columns: 1fr;
  }
}
</style>
