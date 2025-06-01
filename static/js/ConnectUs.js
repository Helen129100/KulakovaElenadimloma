
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
 

    if(e.target.id == "upload") {
    
        beforeSend();
       
        fetch('/videos/add_video/', {
        
        headers:{
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest', 
        },
        })
        .then(response => {
          return response.json() 
        })
        .then(data => {
      
         
          document.getElementById("modal-content").innerHTML = data.video_form;
         
         
        })
         
    }
     
   
});





  
document.addEventListener("click", function(e) {

    
 
    if(e.target.id == "video_submit" ) {
    console.log("error");
    
      let formdata = new FormData();  
 
      let video_file = document.getElementById('id_video_file').files[0];
     
      formdata.append('video_file', video_file ); 
      
      let csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
      
      formdata.append('csrfmiddlewaretoken', csrf);
    
      let post = document.querySelector('input[name="post"]').value;
        
      formdata.append('post',  post)
   
      fetch('/videos/add_video/', {
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
			console.log("error_tem");
           document.getElementById("video-error").textContent  = "Видео не прошло цензуру";
               document.getElementById("modal-content").innerHTML = " ";
               document.getElementById("modal-content").innerHTML = data.video_form;
             
         } else if (data.form_is_valid) {
               $("#staticBackdrop").modal("hide");
               location.reload();  
         }
             
                    
       })
         
    }
     
}); 
  
  
  
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
	


  
