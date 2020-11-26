// 검색창 초기화 버튼 함수
function clearSearchInput(n) {
    var someform = document.getElementsByTagName('form')[n].reset();
  }



// 검색창 접었다 폈다 하기 함수

function foldSearchDiv() {
    var somediv = document.getElementById("searchDiv");
    var infodiv = document.getElementById("userInfoDiv");
    var foldbutton = document.getElementById("searchFoldButton");
    
    // searchDiv가 접혀있으면, searchDiv 켜주기
   if(somediv.style.display === 'none') {
        somediv.style.display = 'block';
        infodiv.style.left = '420px';
        infodiv.style.transform = 'translateX(0)';

        foldbutton.style.left = '380px';
        foldbutton.innerHTML = ' ◀ ';   
    
    }
    // searchDiv가 보이면, searchDiv 를 끄고 FoldButton 내용 바꾸기
    else {
        somediv.style.display = 'none';
        infodiv.style.left = '50%';
        infodiv.style.transform = 'translateX(-50%)';

        foldbutton.style.left = '0';
        foldbutton.innerHTML = ' ▶ ';

    }
}
