function validateForm() {
  const input = document.getElementById("youtube-input");
  const errorMsg = document.getElementById("input-error");
  const value = input.value;
  const pattern =
    /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/(watch\?v=|channel\/|user\/|@)[\w\-]+/;

  if (!pattern.test(value)) {
    input.style.border = "2px solid red";
    errorMsg.style.display = "block";
    errorMsg.innerText =
      "❌ Please enter a valid YouTube video or channel URL.";
    setTimeout(() => {
      input.style.border = "";
      errorMsg.style.display = "none";
    }, 3000);
    return false;
  }

  input.classList.add("search-loading");

  return true;
}

function clearAnalysis() {
  const input = document.getElementById("youtube-input");
  input.value = "";
  input.classList.remove("search-loading");
  const result = document.getElementById("result-container");
  if (result) result.innerHTML = "";
}

window.onload = function () {
  document.getElementById("youtube-input").classList.remove("search-loading");
};
