

/* 순석 추가 코드 */
/* 로그인 페이지 자바스크립트, 모달 팝업용*/
function showModalDiv(n) {
      var modaldiv = document.getElementsByClassName("modalDiv")[n];
      modaldiv.style.display = 'block';

}

function hideModalDiv(n) {
      var modaldiv = document.getElementsByClassName("modalDiv")[n];
      modaldiv.style.display = 'none';
}

function clearModalInput(n) {
  var modal = document.getElementsByTagName('form')[n].reset();
}


function passwordMatch() {
    var password = document.getElementsByName('password')[1].value;
    var passwordconfirm = document.getElementsByName('passwordconfirm')[0].value;

    if(password != passwordconfirm) alert("비밀번호가 서로 일치하지 않습니다.");
  }

  function passwordMatch2() {
    var password = document.getElementsByName('password1')[0].value;
    var passwordconfirm = document.getElementsByName('password2')[0].value;

    if(password != passwordconfirm) alert("비밀번호가 서로 일치하지 않습니다.");
  }