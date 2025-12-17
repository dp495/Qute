document.getElementById('logout').addEventListener('click', function() {
    if (!confirm('确定退出当前身份吗？')) {
        return;
    }
    fetch('/logout/', {
        method: 'POST',
        body: 'logout'
    })
    .then(response => response.json())
    .then(data => {
        if(data.err === 0) {
            window.location.href = '/';
        }else {
            console.error('Error:', data.err);
            alert('网络错误，请重试');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('网络错误，请重试');
    });
});