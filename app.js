document.addEventListener('click', (event) => {
  const link = event.target.closest('a');
  if (!link) return;
  const text = (link.textContent || '').trim();
  if (text.includes('지원 신청') || text.includes('지원하기') || text.includes('신청하기')) {
    link.href = 'https://forms.gle/zZFbDgqRrS6WZeDd9';
    link.target = '_blank';
    link.rel = 'noreferrer';
  }
});
