(function () {
  const dataEl = document.getElementById('dashboard-chart-data');
  if (!dataEl) return;
  const chartData = JSON.parse(dataEl.textContent);

  Chart.defaults.color = '#888';
  Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';

  new Chart(document.getElementById('playsChart'), {
    type: 'line',
    data: {
      labels: chartData.plays_by_day.labels,
      datasets: [{
        label: 'Plays',
        data: chartData.plays_by_day.data,
        borderColor: 'rgba(124,58,237,0.85)',
        backgroundColor: 'rgba(124,58,237,0.15)',
        fill: true, tension: 0.4, pointRadius: 3,
      }]
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
  });

  new Chart(document.getElementById('genreChart'), {
    type: 'doughnut',
    data: {
      labels: chartData.genres.labels,
      datasets: [{
        data: chartData.genres.data,
        backgroundColor: ['#7c3aed','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6'],
        borderWidth: 0,
      }]
    },
    options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }, cutout: '65%' }
  });

  new Chart(document.getElementById('usersChart'), {
    type: 'bar',
    data: {
      labels: chartData.new_users.labels,
      datasets: [{
        label: 'New Users',
        data: chartData.new_users.data,
        backgroundColor: 'rgba(6,182,212,0.85)',
        borderRadius: 4,
      }]
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
  });
})();
