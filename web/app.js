"use strict";
const $ = id => document.getElementById(id);
const statusNames = {recognized:"Đúng mẫu",needs_review:"Cần kiểm tra",no_plate:"Chưa tìm thấy biển",segmentation_empty:"Chưa tách được ký tự",ocr_unavailable:"OCR chưa sẵn sàng",processing_error:"Lỗi xử lý",manual:"Đã chỉnh tay",pending:"Đang xử lý"};
let selectedFile = null, cameraStream = null, offset = 0, total = 0, editingId = null, editingVehicleType = "unknown", busy = false;
const pageSize = 10;
async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = "Không thể xử lý yêu cầu.";
    try { const body = await response.json(); detail = typeof body.detail === "string" ? body.detail : "Thông tin gửi lên chưa hợp lệ."; } catch {}
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}
function message(text, error = false) { $("message").textContent = text; $("message").classList.toggle("error", error); }
function setBusy(value) { busy = value; $("upload-button").disabled = value; $("camera-capture").disabled = value || !cameraStream; $("upload-button").textContent = value ? "Đang xử lý…" : "Bắt đầu nhận diện ↗"; }
function chooseFile(file) { if (!file) return; selectedFile = file; $("file-label").textContent = file.name; message("Đã chọn tệp. Bấm Bắt đầu nhận diện để xử lý."); }
$("file-input").addEventListener("change", event => chooseFile(event.target.files[0]));
for (const name of ["dragenter", "dragover"]) $("drop-zone").addEventListener(name, event => { event.preventDefault(); $("drop-zone").classList.add("drag"); });
for (const name of ["dragleave", "drop"]) $("drop-zone").addEventListener(name, event => { event.preventDefault(); $("drop-zone").classList.remove("drag"); });
$("drop-zone").addEventListener("drop", event => { chooseFile(event.dataTransfer.files[0]); if (selectedFile) { const transfer = new DataTransfer(); transfer.items.add(selectedFile); $("file-input").files = transfer.files; } });
function showImage(id, url) { const node = $(id); node.hidden = !url; if (url) node.src = url; else node.removeAttribute("src"); }
function showResult(record) {
  $("empty-result").hidden = true; $("result-content").hidden = false;
  $("plate-text").textContent = record.plate_text || record.raw_text || "Chưa đọc được";
  $("result-state").textContent = "#" + record.id;
  $("valid-state").textContent = statusNames[record.status] || record.status;
  $("valid-state").classList.toggle("warning", !record.is_valid || record.status === "needs_review");
  const type = {car:"Ô tô",motorcycle:"Xe máy",unknown:"Chưa xác định loại xe"}[record.vehicle_type] || "Chưa xác định loại xe";
  $("result-detail").textContent = [record.province, type, record.confidence == null ? null : "Điểm OCR: " + Math.round(record.confidence * 100) + "%"].filter(Boolean).join(" · ");
  const isVideo = /\.(mp4|avi|mov|mkv|webm)$/i.test(record.image_path || "");
  showImage("source-image", isVideo ? null : record.image_url); showImage("crop-image", record.crop_url);
  $("characters").replaceChildren();
  for (const [index, url] of (record.metadata.character_urls || []).entries()) { const img = document.createElement("img"); img.src = url; img.alt = "Ký tự thứ " + (index + 1); $("characters").append(img); }
  $("char-count").textContent = (record.metadata.num_chars || 0) + " ký tự";
  $("raw-text").textContent = record.raw_text ? "Chuỗi gốc: " + record.raw_text : "Chưa có chuỗi ký tự";
  $("elapsed").textContent = record.metadata.elapsed_ms == null ? "" : Math.round(record.metadata.elapsed_ms) + " ms";
  const steps = record.metadata.processing_images || [];
  $("processing-details").hidden = !steps.length;
  $("processing-images").replaceChildren();
  for (const step of steps) { const figure=document.createElement("figure"), image=document.createElement("img"), caption=document.createElement("figcaption"); image.src=step.url; image.alt=step.label; caption.textContent=step.label; figure.append(image,caption); $("processing-images").append(figure); }
  const methods={otsu_dark:"Otsu",otsu_light:"Otsu, chữ sáng",clahe_otsu:"CLAHE + Otsu",adaptive_31:"Ngưỡng thích nghi Gaussian 31×31",adaptive_51:"Ngưỡng thích nghi Gaussian 51×51",detail_31:"Giữ chi tiết + Gaussian 31×31",detail_51:"Giữ chi tiết + Gaussian 51×51"};
  $("processing-note").textContent=(methods[record.metadata.threshold_method] || "")+(record.metadata.frame_cleanup ? " · Lọc viền bằng morphology" : "")+(record.metadata.ocr_requires_review ? " · Ký tự chưa đủ rõ, cần đối chiếu ảnh gốc." : "");
}
async function upload(file) {
  if (busy) return;
  setBusy(true);
  const video = file.type.startsWith("video/") || /\.(mp4|avi|mov|mkv|webm)$/i.test(file.name);
  message(video ? "Đang xử lý video. Các khung hình được lưu vào lịch sử khi hoàn thành." : "Đang tìm biển số và đọc ký tự…");
  const body = new FormData(); body.append("file", file); body.append("vehicle_type", $("vehicle-type").value);
  try {
    const result = await api("/api/upload/" + (video ? "video" : "image"), {method:"POST",body});
    if (video) { const best = [...result.items].reverse().find(item => item.crop_url) || result.items.at(-1); if (best) showResult(best); message("Đã xử lý " + result.frames_processed + " khung hình; tìm thấy vùng biển trong " + result.detections + " khung hình."); }
    else { showResult(result); message("Đã lưu kết quả #" + result.id + ". " + (statusNames[result.status] || "Hoàn tất.")); }
    offset = 0; await refresh();
  } catch (error) { message(error.message, true); }
  finally { setBusy(false); }
}
$("upload-form").addEventListener("submit", event => { event.preventDefault(); if (selectedFile) upload(selectedFile); else message("Hãy chọn một tệp trước.", true); });
async function refresh() {
  const [history, stats, health] = await Promise.all([api(`/api/plates?limit=${pageSize}&offset=${offset}&q=${encodeURIComponent($("search").value)}`),api("/api/stats"),api("/api/health")]);
  total = history.total; $("history-count").textContent = total;
  $("stat-total").textContent = stats.total; $("stat-valid").textContent = stats.valid; $("stat-review").textContent = stats.total - stats.valid;
  $("model-status").textContent = health.ocr_ready ? "● OCR sẵn sàng" : "● Đang thiếu mô hình OCR";
  $("model-status").classList.toggle("warning", !health.ocr_ready);
  $("history-body").replaceChildren();
  for (const record of history.items) {
    const row = document.createElement("tr");
    const time = new Date(record.timestamp).toLocaleString("vi-VN", {timeZone:"Asia/Ho_Chi_Minh",hour12:false});
    for (const text of [record.plate_text || record.raw_text || "—",record.province || "—",time,statusNames[record.status] || record.status]) { const cell = document.createElement("td"); cell.textContent = text; row.append(cell); }
    const actions = document.createElement("td"), group = document.createElement("div"); group.className = "table-actions";
    for (const [label, callback, className] of [["Xem",() => { showResult(record); $("recognize").scrollIntoView(); },""],["Sửa",() => { editingId = record.id; editingVehicleType = record.vehicle_type || "unknown"; $("edit-text").value = record.plate_text || record.raw_text || ""; $("edit-dialog").showModal(); },""],["Xóa",async () => { if (confirm("Xóa bản ghi #" + record.id + " khỏi lịch sử?")) { try { await api("/api/plates/" + record.id,{method:"DELETE"}); if (offset && history.items.length === 1) offset = Math.max(0,offset-pageSize); await refresh(); } catch(error) { message(error.message,true); } } },"delete"]]) {
      const button = document.createElement("button"); button.type = "button"; button.textContent = label; button.className = className; button.addEventListener("click",callback); group.append(button);
    }
    actions.append(group); row.append(actions); $("history-body").append(row);
  }
  if (!history.items.length) { const row = document.createElement("tr"), cell = document.createElement("td"); cell.colSpan = 5; cell.className = "empty-history"; cell.textContent = "Chưa có kết quả phù hợp."; row.append(cell); $("history-body").append(row); }
  $("previous").disabled = offset === 0; $("next").disabled = offset + pageSize >= total; $("page-info").textContent = total ? `${offset + 1}–${Math.min(offset + pageSize,total)} / ${total}` : "";
}
$("previous").addEventListener("click",() => { offset = Math.max(0,offset-pageSize); refresh().catch(error => message(error.message,true)); });
$("next").addEventListener("click",() => { offset += pageSize; refresh().catch(error => message(error.message,true)); });
$("refresh").addEventListener("click",() => refresh().catch(error => message(error.message,true)));
let searchTimeout; $("search").addEventListener("input",() => { clearTimeout(searchTimeout); searchTimeout = setTimeout(() => { offset=0; refresh().catch(error => message(error.message,true)); },300); });
$("edit-cancel").addEventListener("click",() => $("edit-dialog").close());
$("edit-form").addEventListener("submit",async event => { event.preventDefault(); try { const record = await api("/api/plates/" + editingId,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({plate_text:$("edit-text").value,vehicle_type:editingVehicleType})}); $("edit-dialog").close(); showResult(record); await refresh(); } catch(error) { message(error.message,true); } });
$("camera-open").addEventListener("click",async () => { try { if (cameraStream) return; cameraStream = await navigator.mediaDevices.getUserMedia({video:true,audio:false}); $("camera").srcObject = cameraStream; $("camera").hidden = false; $("camera-stop").hidden = false; $("camera-capture").disabled = busy; message("Webcam đã mở. Bấm Chụp & nhận diện khi biển số hiện rõ."); } catch { message("Không mở được webcam. Hãy kiểm tra camera và quyền truy cập của trình duyệt.",true); } });
function stopCamera() { if (cameraStream) cameraStream.getTracks().forEach(track => track.stop()); cameraStream = null; $("camera").srcObject = null; $("camera").hidden = true; $("camera-stop").hidden = true; $("camera-capture").disabled = true; }
$("camera-stop").addEventListener("click",stopCamera); window.addEventListener("beforeunload",stopCamera);
$("camera-capture").addEventListener("click",() => { const video=$("camera"); if (!cameraStream || !video.videoWidth) return; const canvas=document.createElement("canvas"); canvas.width=video.videoWidth; canvas.height=video.videoHeight; canvas.getContext("2d").drawImage(video,0,0); canvas.toBlob(blob => { if (blob) upload(new File([blob],"webcam.jpg",{type:"image/jpeg"})); },"image/jpeg",.92); });
refresh().catch(() => { $("model-status").textContent = "● Mất kết nối"; message("Không kết nối được máy chủ local.",true); });
