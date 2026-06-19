// 自动检测后端地址：通过 Flask 访问时用同源，直接打开文件时用 localhost:8080
(function() {
    var protocol = window.location.protocol;
    if (protocol === 'file:') {
        // 通过 file:// 协议直接打开，需要指定后端地址
        axios.defaults.baseURL = "http://localhost:8080";
    } else {
        // 通过 Flask 服务器访问，使用同源请求
        axios.defaults.baseURL = "";
    }
})();

// axios 响应拦截器：统一处理错误，从 400/500 响应中提取后端错误消息
axios.interceptors.response.use(
    function(response) {
        return response;
    },
    function(error) {
        // 如果后端返回了 JSON 格式的错误消息，提取出来
        if (error.response && error.response.data && error.response.data.msg) {
            error.userMessage = error.response.data.msg;
        } else if (error.response && error.response.status === 400) {
            error.userMessage = '请求参数错误(400)';
        } else if (error.response && error.response.status === 500) {
            error.userMessage = '服务器内部错误(500)';
        } else if (error.code === 'ERR_NETWORK') {
            error.userMessage = '无法连接服务器，请确认后端已启动';
        } else {
            error.userMessage = '网络请求失败: ' + (error.message || '未知错误');
        }
        return Promise.reject(error);
    }
);

// 安全读写 localStorage（file:// 协议下可能被阻止）
var _localStorageAvailable = null;
function isLocalStorageAvailable() {
    if (_localStorageAvailable !== null) return _localStorageAvailable;
    try {
        var testKey = '__test__';
        localStorage.setItem(testKey, '1');
        localStorage.removeItem(testKey);
        _localStorageAvailable = true;
    } catch(e) {
        console.warn('localStorage 不可用（可能被浏览器阻止）:', e.message);
        _localStorageAvailable = false;
    }
    return _localStorageAvailable;
}

// 内存降级存储（当 localStorage 不可用时）
var _memoryStore = {};

function safeGetItem(key) {
    if (isLocalStorageAvailable()) {
        return localStorage.getItem(key);
    }
    return _memoryStore[key] || null;
}

function safeSetItem(key, value) {
    if (isLocalStorageAvailable()) {
        try {
            localStorage.setItem(key, value);
            return;
        } catch(e) {
            console.warn('localStorage 写入失败，使用内存存储');
        }
    }
    _memoryStore[key] = value;
}

function safeRemoveItem(key) {
    if (isLocalStorageAvailable()) {
        localStorage.removeItem(key);
    }
    delete _memoryStore[key];
}

// 图片地址解析：file:// 模式下补全后端地址
function resolveImgUrl(url) {
    if (!url) return url;
    // 已经是完整 URL（http/https/data:），不做处理
    if (/^https?:\/\//i.test(url) || /^data:/i.test(url)) return url;
    // file:// 协议下需要补全后端地址
    if (window.location.protocol === 'file:') {
        var base = axios.defaults.baseURL || 'http://localhost:8080';
        return base + (url.startsWith('/') ? url : '/' + url);
    }
    // Flask 托管模式，直接返回相对路径
    return url;
}

// 全局保存当前登录用户
var currentUser = JSON.parse(safeGetItem("currentUser")) || null;

// 保存登录用户
function saveUser(user){
    safeSetItem("currentUser", JSON.stringify(user));
    currentUser = user;
}

// 退出登录
function logout(){
    safeRemoveItem("currentUser");
    currentUser = null;
    window.location.href = "index.html";
}

// ========== 商品相关接口 ==========
// 获取全部商品
async function getGoodsList(){
    var res = await axios.get("/api/goods/list");
    return res.data.data;
}

// 模糊搜索商品
async function searchGoods(keyword){
    var res = await axios.get("/api/goods/search",{params:{keyword:keyword}});
    return res.data.data;
}

// 按分类获取商品
async function getGoodsByCategory(category){
    var res = await axios.get("/api/goods/category",{
        params:{category:category}
    });
    return res.data.data;
}

// 获取商品详情
async function getGoodsDetail(id){
    var res = await axios.get("/api/goods/detail",{params:{id:id}});
    return res.data.data;
}

// 发布商品
async function publishGoods(data){
    var res = await axios.post("/api/goods/publish", data);
    return res.data;
}

// 获取我的发布
async function getMyPublish(userId){
    var res = await axios.get("/api/goods/myPublish",{params:{userId:userId}});
    return res.data.data;
}

// 删除我的发布
async function delGoods(id){
    if(!currentUser) return {code:400, msg:'未登录'};
    var res = await axios.delete("/api/goods/delete",{params:{id:id, userId: currentUser.id}});
    return res.data;
}

// ========== 购物车接口 ==========
// 加入购物车
async function addToCart(goodsId){
    if(!currentUser){
        alert("请先登录！");
        window.location.href = "login.html";
        return;
    }
    var params = {
        userId: currentUser.id,
        goodsId: goodsId,
        count: 1
    };
    var res = await axios.post("/api/cart/add", params);
    alert(res.data.msg);
}

// 获取购物车列表
async function getCartList(userId){
    var res = await axios.get("/api/cart/list",{params:{userId:userId}});
    return res.data.data;
}

// 修改购物车数量
async function updateCartCount(cartId, count){
    await axios.put("/api/cart/update", null,{
        params:{id:cartId, count:count}
    });
}

// 删除购物车
async function delCartItem(cartId){
    await axios.delete("/api/cart/delete",{params:{id:cartId}});
}

// 提交订单
async function submitOrder(userId){
    var res = await axios.post("/api/cart/submit", { userId: userId });
    return res.data;
}

// 获取订单列表
async function getOrderList(userId){
    var res = await axios.get("/api/cart/orders",{params:{userId:userId}});
    return res.data.data;
}

// ========== 退货接口 ==========
// 申请退货
async function requestReturn(userId, orderId, reason){
    var res = await axios.post("/api/cart/orders/return/request", {
        userId: userId,
        orderId: orderId,
        reason: reason
    });
    return res.data;
}

// 获取退货申请列表（买家/卖家）
async function getReturnList(userId, role){
    var res = await axios.get("/api/cart/orders/return/list",{
        params:{userId: userId, role: role || 'buyer'}
    });
    return res.data.data;
}

// 处理退货申请（卖家）
async function handleReturn(returnId, action, sellerId, sellerReply){
    var res = await axios.put("/api/cart/orders/return/handle", {
        returnId: returnId,
        action: action,
        sellerId: sellerId,
        sellerReply: sellerReply || ''
    });
    return res.data;
}

// 检查订单退货状态
async function checkReturnStatus(orderId, userId){
    var res = await axios.get("/api/cart/orders/return/check",{
        params:{orderId: orderId, userId: userId}
    });
    return res.data.data;
}

// ========== 收藏接口 ==========
// 加入收藏
async function addToCollect(goodsId){
    if(!currentUser){
        alert("请先登录！");
        window.location.href = "login.html";
        return;
    }
    var params = {
        userId: currentUser.id,
        goodsId: goodsId
    };
    var res = await axios.post("/api/collect/add", params);
    alert(res.data.msg);
}

// 取消收藏
async function cancelCollect(userId, goodsId){
    await axios.delete("/api/collect/delete",{
        params:{userId:userId, goodsId:goodsId}
    });
}

// 获取我的收藏
async function getCollectList(userId){
    var res = await axios.get("/api/collect/list",{params:{userId:userId}});
    return res.data.data;
}

// ========== 消息接口 ==========
// 发送消息
async function sendMessage(data){
    var res = await axios.post("/api/messages/send", data);
    return res.data;
}

// 获取消息列表（收到的消息）
async function getMessageList(userId){
    var res = await axios.get("/api/messages/list",{params:{userId:userId}});
    return res.data.data;
}

// 获取对话列表（所有对话对象）
async function getConversations(userId){
    var res = await axios.get("/api/messages/conversations",{params:{userId:userId}});
    return res.data.data;
}

// 获取与指定用户的聊天记录
async function getChatHistory(userId, partnerId){
    var res = await axios.get("/api/messages/chat",{params:{userId:userId, partnerId:partnerId}});
    return res.data.data;
}

// ========== 收藏状态查询 ==========
async function checkCollectStatus(userId, goodsId){
    var res = await axios.get("/api/collect/check",{params:{userId:userId, goodsId:goodsId}});
    return res.data.data.collected;
}

// ========== 图片上传 ==========
async function uploadImage(file){
    var formData = new FormData();
    formData.append('file', file);
    var res = await axios.post("/api/goods/upload", formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
}

// ========== 编辑个人资料 ==========
async function updateProfile(userId, nickname){
    var res = await axios.put("/api/user/update", { userId: userId, nickname: nickname });
    return res.data;
}

// 修改密码
async function changePassword(userId, oldPassword, newPassword){
    var res = await axios.put("/api/user/changePassword", {
        userId: userId,
        oldPassword: oldPassword,
        newPassword: newPassword
    });
    return res.data;
}