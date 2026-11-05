/**
 * BlogSphere - Main Client-Side JavaScript
 * Handles AJAX likes, comment editing modals, delete confirmations,
 * image previews, and UI enhancements.
 */

document.addEventListener('DOMContentLoaded', function () {
  // Initialize all Bootstrap tooltips & popovers
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Auto-dismiss alerts after 5 seconds
  const autoDismissAlerts = document.querySelectorAll('.alert-dismiss-auto');
  autoDismissAlerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // Setup Global CSRF Token for fetch()
  const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';

  // ------------------------------------------------------------------------
  // AJAX Like Button Handling
  // ------------------------------------------------------------------------
  const likeButtons = document.querySelectorAll('.btn-like');
  likeButtons.forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const postId = btn.dataset.postId;
      if (!postId) return;

      const heartIcon = btn.querySelector('.like-icon');
      const countSpan = btn.querySelector('.like-count');

      // Add bounce animation
      btn.classList.add('disabled');

      fetch(`/blog/${postId}/like`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'Accept': 'application/json'
        }
      })
      .then(response => {
        if (response.status === 401) {
          window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
          return null;
        }
        return response.json();
      })
      .then(data => {
        btn.classList.remove('disabled');
        if (!data) return;

        if (data.status === 'success') {
          if (data.liked) {
            btn.classList.add('liked');
            if (heartIcon) {
              heartIcon.classList.remove('bi-heart');
              heartIcon.classList.add('bi-heart-fill');
            }
          } else {
            btn.classList.remove('liked');
            if (heartIcon) {
              heartIcon.classList.remove('bi-heart-fill');
              heartIcon.classList.add('bi-heart');
            }
          }

          if (countSpan && typeof data.total_likes !== 'undefined') {
            countSpan.textContent = data.total_likes;
          }
        } else if (data.message) {
          alert(data.message);
        }
      })
      .catch(err => {
        btn.classList.remove('disabled');
        console.error('Like toggle error:', err);
      });
    });
  });

  // ------------------------------------------------------------------------
  // Universal Delete Confirmation Modal Setup
  // ------------------------------------------------------------------------
  const deleteModal = document.getElementById('deleteConfirmModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      if (!button) return;

      const itemType = button.getAttribute('data-item-type') || 'item';
      const itemName = button.getAttribute('data-item-name') || '';
      const actionUrl = button.getAttribute('data-action-url') || '';

      const modalTitle = deleteModal.querySelector('#deleteModalTitle');
      const modalBodyText = deleteModal.querySelector('#deleteModalBodyText');
      const deleteForm = deleteModal.querySelector('#deleteModalForm');

      if (modalTitle) {
        modalTitle.textContent = `Confirm Delete ${itemType}`;
      }
      if (modalBodyText) {
        modalBodyText.innerHTML = `Are you sure you want to permanently delete <strong>"${escapeHtml(itemName)}"</strong>? This action cannot be undone.`;
      }
      if (deleteForm && actionUrl) {
        deleteForm.setAttribute('action', actionUrl);
      }
    });
  }

  // ------------------------------------------------------------------------
  // Comment Edit Modal Setup
  // ------------------------------------------------------------------------
  const editCommentModal = document.getElementById('editCommentModal');
  if (editCommentModal) {
    editCommentModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      if (!button) return;

      const commentId = button.getAttribute('data-comment-id');
      const commentContent = button.getAttribute('data-comment-content');
      const updateUrl = button.getAttribute('data-update-url');

      const form = editCommentModal.querySelector('#editCommentForm');
      const textarea = editCommentModal.querySelector('#editCommentTextarea');

      if (form && updateUrl) {
        form.setAttribute('action', updateUrl);
      }
      if (textarea && commentContent) {
        textarea.value = commentContent;
      }
    });
  }

  // ------------------------------------------------------------------------
  // Image Upload Instant Preview
  // ------------------------------------------------------------------------
  const imageInputs = document.querySelectorAll('.image-preview-input');
  imageInputs.forEach(function (input) {
    input.addEventListener('change', function () {
      const targetPreviewId = input.dataset.previewTarget;
      const previewImg = document.getElementById(targetPreviewId);
      const previewContainer = document.getElementById(targetPreviewId + 'Container');

      if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
          if (previewImg) {
            previewImg.src = e.target.result;
          }
          if (previewContainer) {
            previewContainer.classList.remove('d-none');
          }
        };
        reader.readAsDataURL(input.files[0]);
      }
    });
  });

  // ------------------------------------------------------------------------
  // Copy to Clipboard (Share button)
  // ------------------------------------------------------------------------
  const copyButtons = document.querySelectorAll('.btn-copy-link');
  copyButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const urlToCopy = btn.dataset.copyUrl || window.location.href;
      navigator.clipboard.writeText(urlToCopy).then(() => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
        btn.classList.add('btn-success');
        btn.classList.remove('btn-outline-secondary');
        setTimeout(() => {
          btn.innerHTML = originalHtml;
          btn.classList.remove('btn-success');
          btn.classList.add('btn-outline-secondary');
        }, 2000);
      }).catch(err => {
        console.error('Failed to copy: ', err);
      });
    });
  });

  // ------------------------------------------------------------------------
  // Helper: Escape HTML string
  // ------------------------------------------------------------------------
  function escapeHtml(string) {
    const div = document.createElement('div');
    div.innerText = string;
    return div.innerHTML;
  }
});
