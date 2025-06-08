
if( document.getElementById('vid') ) {

  document.getElementById('vid').currentTime = 57;
  
}


function beforeSend() {
  $("#staticBackdrop .modal-content").html("");
  $("#staticBackdrop").modal("show");
   
}


document.addEventListener("click",  function(e) {

    if(e.target.id == "remove") {
    
       let formdata = new FormData(); 
   
       let comment_id = e.target.getAttribute('data-id');
      
       let csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
       
       formdata.append( 'comment_id', comment_id ); 
       
       formdata.append('csrfmiddlewaretoken', csrf);
       
       fetch('/videos/remove/', {
           method: 'POST',
           mode: 'same-origin',  
           headers:{
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
           },
           body:formdata 
           })
           .then(response => {
           return response.json() 
           })
           .then(data => {
           
             let commentcontainer = document.getElementById('commentcontainer');
             
             commentcontainer.innerHTML = data.partial_video_comments
             
             document.getElementById("commentcount").textContent=data.comment_count;
                    
                    
           })
           
    }
    
  
  });


document.addEventListener("keydown",  function(e) {

    

    if(e.target.id == "usercomment") {
    
      if (e.keyCode == 13) {
      
         let form = document.querySelector('#comment');

         let data = new FormData(form);

         let csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
         
         data.append('csrfmiddlewaretoken', csrf);
         
         fetch('/videos/comment/', {
           method: 'POST',
           mode: 'same-origin',  
           headers:{
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf,
           },
           body:data 
           })
           .then(response => {
           return response.json() 
           })
           .then(data => {
                
             if (Object.entries(data).length != 0) {
             
                 let commentcontainer = document.getElementById('commentcontainer');
             
                 commentcontainer.innerHTML = data.partial_video_comments
             
                 document.getElementById("commentcount").textContent=data.comment_count;
             
                 document.getElementById('usercomment').value = ''
         
             }
         
                    
           })
        
     
      }
         
    }
      
});





document.addEventListener("click", function(e) {
    if (e.target.id == "upload") {
        beforeSend();

        fetch('/videos/add_video/', {
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById("modal-content").innerHTML = data.video_form;

            // 🔥 ВАЖНО: инициализация скрипта после вставки HTML
            initVideoUploadEvents();
        });
    }
});




document.addEventListener('DOMContentLoaded', () => {
 document.addEventListener("click", async function(e) {
    if (e.target.id === "video_submit") {
		console.log("video_prob");
        let formdata = new FormData();
        let video_file = document.getElementById('id_video_file').files[0];
        let csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
        let post = document.querySelector('input[name="post"]').value;

        formdata.append('video_file', video_file);
        formdata.append('post', post);
        formdata.append('csrfmiddlewaretoken', csrf);

        fetch('/videos/add_video/', {
            method: 'POST',
            mode: 'same-origin',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrf,
            },
            body: formdata
        })
            .then(response => response.json())
            .then(data => {
                if (!data.form_is_valid) {
                    
               

                    document.getElementById("modal-content").innerHTML = data.video_form;

                    // Показать блок с предупреждением
                    setTimeout(() => {
                        document.getElementById("censorship-warning").style.display = "block";
                    }, 300);
                } else {
                    $("#staticBackdrop").modal("hide");
                    location.reload();
                }
            });
    }

   const resultDiv = document.getElementById('text_result_censorship');


    if (e.target.id === "start_censorship") {
      
        resultDiv.innerHTML = '<div class="text-info">Обработка видео...</div>';

        const formdata = new FormData();
        const video_file = document.getElementById('id_video_file').files[0];
        const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
        const post = document.querySelector('input[name="post"]').value;

        formdata.append('video_file', video_file);
        formdata.append('post', post);
        formdata.append('csrfmiddlewaretoken', csrf);

        try {
            const response = await fetch('/videos/check_censure/', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formdata
            });

            const data = await response.json();
if (data.success) {
    resultDiv.innerHTML = `<div class="text-success">${data.message}</div>`;
document.querySelector('.edit_censorship').style.display = 'block';
    const editLink = document.querySelector('.edit_censorship a');
  if (data.video_url && data.json_video_path) {
  const urlEncoded = encodeURIComponent(data.video_url);
  const jsonEncoded = data.json_video_path;
console.log(jsonEncoded);
  const baseEditorUrl = document.querySelector('.edit_censorship').dataset.editorUrl;
  editLink.href = `${baseEditorUrl}?video=${urlEncoded}&json_video=${jsonEncoded}`;
  editLink.style.display = 'inline-block';
}
} else {
    resultDiv.innerHTML = `<div class="text-danger">${data.message}</div>`;
}
          

        } catch (error) {
            resultDiv.innerHTML = `<div class="text-danger">Ошибка: ${error.message}</div>`;
        }
    }
        
            
        if (e.target.id === "cancel_upload") {
            // Просто скрываем кнопки и показываем сообщение
            e.target.style.display = 'none';
            document.getElementById('start_censorship').style.display = 'none';
            resultDiv.innerHTML = '<div class="text-warning">Видео загружено без цензуры</div>';
        }
});
     function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
  
  
document.addEventListener("click", function(e) {

    if(e.target.id == "edit") {
        
        let video_id = e.target.getAttribute('data-id');
                 
        beforeSend();
      
        fetch('/videos/edit_video/' + video_id + "/", {
        headers:{
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest', 
        },
        })
        .then(response => {
          return response.json() 
        })
        .then(data => {
        
         
         document.getElementById("modal-content").innerHTML = data.edit_video;
         
         
        })
        
    }
     
});

});

  
document.addEventListener("click", function(e) {
 
    if(e.target.id == "submit_edited_video" ) {
    
      let formdata = new FormData();  
   
      let video_file = document.getElementById('id_video_file').files[0];
      
      formdata.append( 'video_file', video_file ); 
    
      let csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
      
      formdata.append('csrfmiddlewaretoken', csrf);
    
      let post = document.getElementById('id_post').value;
    
      formdata.append('post', post)
      
      let video_id = e.target.getAttribute('data-id');
      
      fetch('/videos/edit_video/' + video_id + "/", {
       method: 'POST',
       mode: 'same-origin',  
       headers:{
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest', 
        'X-CSRFToken': csrf,
      },
      body: formdata 
      })
      .then(response => {
         return response.json() 
      })
      .then(data => {
      
     
         if (!data.form_is_valid){
          
               document.getElementById("modal-content").innerHTML = " ";
               document.getElementById("modal-content").innerHTML = data.edited_video;
             
         } else if (data.form_is_valid) {
               $("#staticBackdrop").modal("hide");
               location.reload();  
         }
         
         
                    
       })
       
        
    }
     
    
}); 
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.querySelector('.theme-toggle');
    const body = document.body;
    const images = document.querySelectorAll('.nav-item_img');
    const nav_text = document.querySelectorAll('.nav-item');
    const currentURL = window.location.href;
    let nav_label = ['Главная', 'Мои подписки', 'Понравившиеся'];
    let page_flag = 0;

    function page_option() {
        if (!currentURL.includes('/video') && page_flag != 1) {
            let nav_label_itter = 0;
            nav_text.forEach(item => {
                item.innerHTML += nav_label[nav_label_itter];
                nav_label_itter++;
            });
            page_flag = 1;
        }
        else {
            nav_text.forEach(item => {
                item.style.width = '45px';
            });
        }
    }

    function changeIconColor(theme) {
        images.forEach(img => {
            const newSrc = theme === 'dark' 
                ? img.src.replace('black.png', 'white.png')
                : img.src.replace('white.png', 'black.png');
            img.src = newSrc;
        });
        changeLikeIconColor(theme);
    }

    // Инициализация
    page_option();
    
    if (themeToggle) {
        // Проверка сохранённой темы
        if (localStorage.getItem('theme') === 'dark') {
            body.classList.add('dark-theme');
            changeIconColor('dark');
        }

        // Обработчик клика
        themeToggle.addEventListener('click', function() {
            const isDark = body.classList.toggle('dark-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            changeIconColor(isDark ? 'dark' : 'light');
        });
    }
});

	
	function changeLikeIconColor(color) {
		const likeIcon = document.getElementById('like_img'); // Селектор вашего изображения лайка
		if (likeIcon) {
let modifiedString = likeIcon.src.slice(0, -9);
			console.log("not "+modifiedString);

			if (color === 'white') {
				modifiedString += "white.png";
			} else {
				modifiedString += "black.png";
			}
			console.log(modifiedString);
			likeIcon.src=modifiedString;
		}
	}
function initVideoUploadEvents() {
	const dropZone = document.querySelector('.drop-zone');
	const fileInput = document.querySelector('#id_video_file');
	const prompt = document.querySelector('.drop-zone__prompt');

	if (!dropZone || !fileInput || !prompt) {
		console.warn("⛔ Не найдены элементы модалки для загрузки видео.");
		return;
	}

	console.log("✅ Инициализация drop zone выполнена");

	dropZone.addEventListener('click', () => {
		fileInput.click();
		console.log("📥 Клик по зоне drop");
	});

	['dragenter', 'dragover'].forEach(eventName => {
		dropZone.addEventListener(eventName, (e) => {
			e.preventDefault();
			e.stopPropagation();
			dropZone.classList.add('drop-zone--over');
		}, false);
	});

	['dragleave', 'drop'].forEach(eventName => {
		dropZone.addEventListener(eventName, (e) => {
			e.preventDefault();
			e.stopPropagation();
			dropZone.classList.remove('drop-zone--over');
		}, false);
	});

	dropZone.addEventListener('drop', (e) => {
		const dt = e.dataTransfer;
		const files = dt.files;
		if (files.length) {
			fileInput.files = files;
			updatePrompt(files[0].name);
		}
	});

	fileInput.addEventListener('change', () => {
		if (fileInput.files.length) {
			updatePrompt(fileInput.files[0].name);
		}
	});

	function updatePrompt(fileName) {
		prompt.textContent = "Файл выбран:";
		prompt.style.fontWeight = "normal";
		prompt.style.color = "#333";

		const fileInfo = document.getElementById("file-info");
		const fileNameDisplay = document.getElementById("file-name-display");

		fileNameDisplay.textContent = "✅ " + fileName;
		fileInfo.style.display = "block";
	}
}
