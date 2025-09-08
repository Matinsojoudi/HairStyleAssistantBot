function toPersianNumber(num) {
    const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
    const englishDigits = '0123456789';
    return num.toString().replace(/[0-9]/g, function(match) {
        return persianDigits[englishDigits.indexOf(match)];
    });
}
function getCurrentWeekDaysEn() {
    return ["saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"];
}
function updateWeekTitle() {
    document.getElementById('currentWeekInfo').textContent = 'هفته جاری (شنبه تا جمعه)';
}

function getCurrentTime() {
    const now = new Date();
    return now.getHours() * 60 + now.getMinutes(); // تبدیل به دقیقه
}

function timeToMinutes(timeString) {
    if (!timeString) return 0;
    const parts = timeString.split(':');
    if (parts.length >= 2) {
        return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    }
    return 0;
}

let reservationsData = [];
let servicesData = {};
let staffData = {};
let usersData = {};

async function loadReservationsData() {
    document.getElementById('loadingIndicator').style.display = 'block';
    document.getElementById('scheduleTable').style.display = 'none';
    try {
        const response = await fetch(
            'https://api.telbotland.ir/api/barbershop_data?database=Amin_barbershop1369_bot.db',
            { headers: { "Authorization": "Matinisthebest_808808" } }
        );
        if (!response.ok) throw new Error('خطا در اتصال به سرور!');
        const data = await response.json();
        usersData = {};
        if (data.users) {
            data.users.forEach(user => {
                usersData[user.chat_id?.toString()] = {
                    first_name: user.first_name || "",
                    last_name: user.last_name || ""
                };
            });
        }
        if (data.user_info) {
            data.user_info.forEach(userInfo => {
                usersData[userInfo.chat_id?.toString()] = {
                    first_name: (userInfo.full_name?.split(' ')[0]) || "",
                    last_name: (userInfo.full_name?.split(' ').slice(1).join(' ')) || ""
                };
            });
        }
        servicesData = {};
        if (data.services) {
            data.services.forEach(service => {
                servicesData[service.id] = {
                    name: service.name,
                    price: service.price
                };
            });
        }
        staffData = {};
        if (data.staff) {
            data.staff.forEach(staff => {
                staffData[staff.id] = {
                    name: staff.name
                };
            });
        }
        const currentWeekDays = getCurrentWeekDaysEn();
        reservationsData = (data.reservations || []).filter(reservation =>
            currentWeekDays.includes((reservation.day || "").toLowerCase())
        );
        renderSchedule();
        updateStats();
        renderTodayReservations();
        document.getElementById('statusIndicator').className = 'status-indicator status-online';
        document.getElementById('statusIndicator').innerHTML = '<i class="fas fa-wifi"></i> آنلاین';
    } catch (error) {
        document.getElementById('statusIndicator').className = 'status-indicator status-offline';
        document.getElementById('statusIndicator').innerHTML = '<i class="fas fa-wifi"></i> آفلاین';
    } finally {
        document.getElementById('loadingIndicator').style.display = 'none';
        document.getElementById('scheduleTable').style.display = 'table';
    }
}
function extractHourFromTimeSlot(slot) {
    if (!slot) return "";
    let parts = slot.split(":");
    if (parts.length >= 2) {
        return parts[0].padStart(2, '0') + ":00";
    }
    return slot;
}
function findReservationsForDayTime(day, timeSlot) {
    return reservationsData.filter(res =>
        (res.day || "").toLowerCase() === day.toLowerCase() &&
        extractHourFromTimeSlot(res.time_slot) === timeSlot
    );
}
function renderSchedule() {
    const scheduleBody = document.getElementById('scheduleBody');
    scheduleBody.innerHTML = '';
    const weekDays = getCurrentWeekDaysEn();
    const timeSlots = [];
    for (let hour = 8; hour < 24; hour++) {
        timeSlots.push(`${hour.toString().padStart(2, '0')}:00`);
    }
    timeSlots.forEach(timeSlot => {
        const row = document.createElement('tr');
        const timeCell = document.createElement('td');
        timeCell.className = 'time-slot';
        timeCell.textContent = toPersianNumber(timeSlot);
        row.appendChild(timeCell);
        weekDays.forEach(day => {
            const cell = document.createElement('td');
            const reservations = findReservationsForDayTime(day, timeSlot);
            if (reservations.length > 0) {
                reservations.forEach((reservation, index) => {
                    const reservationDiv = document.createElement('div');
                    reservationDiv.className = 'reservation';
                    if (index > 0) reservationDiv.style.marginTop = '5px';
                    const user = usersData[reservation.user_id?.toString()];
                    const customerName = user ? `${user.first_name} ${user.last_name}`.trim() : 'نامشخص';
                    const staff = staffData[reservation.staff_id];
                    const staffName = staff ? staff.name : 'نامشخص';
                    let serviceIds = [];
                    if (reservation.services) {
                        serviceIds = reservation.services.toString().split(',').map(id => parseInt(id)).filter(x => !isNaN(x));
                    }
                    const serviceNames = serviceIds.map(id => servicesData[id]?.name || 'خدمت').join('، ');
                    const displayServices = serviceNames.length > 15 ? serviceNames.substring(0, 15) + '...' : serviceNames;
                    reservationDiv.innerHTML =
                        '<div class="reservation-name">' + customerName + '</div>' +
                        '<div class="reservation-staff">آرایشگر: ' + staffName + '</div>' +
                        '<div class="reservation-services">' + displayServices + '</div>' +
                        '<div class="reservation-price">' + toPersianNumber(reservation.total_price?.toLocaleString() || "۰") + ' تومان</div>';
                    cell.appendChild(reservationDiv);
                });
            } else {
                cell.innerHTML = '<span class="empty-slot">آزاد</span>';
            }
            row.appendChild(cell);
        });
        scheduleBody.appendChild(row);
    });
}

function renderTodayReservations() {
const weekDays = getCurrentWeekDaysEn();
const jsDay = new Date().getDay();
const todayDay = weekDays[jsDay === 6 ? 0 : jsDay + 1];
const currentTimeMinutes = getCurrentTime();

// فیلتر رزروهای امروز که هنوز شروع نشده‌اند
const todayReservations = reservationsData.filter(res => {
    if ((res.day || "").toLowerCase() !== todayDay.toLowerCase()) return false;
    const reservationTimeMinutes = timeToMinutes(res.time_slot);
    return reservationTimeMinutes >= currentTimeMinutes;
});

const container = document.getElementById("todayReservationsContainer");
const grid = document.getElementById("todayReservationsGrid");

grid.innerHTML = '';

// این خط درست شد: همیشه کانتینر رو نشون بده، پیام رو توی grid بزار
container.style.display = "block";

if (!todayReservations.length) {
    grid.innerHTML = `
        <div class="no-reservations">
            <i class="fas fa-calendar-check"></i>
            <div>رزرو باقی‌مانده‌ای برای امروز وجود ندارد</div>
        </div>
    `;
    return;
}

// مرتب‌سازی بر اساس زمان
todayReservations.sort((a, b) => {
    const timeA = timeToMinutes(a.time_slot);
    const timeB = timeToMinutes(b.time_slot);
    return timeA - timeB;
});

todayReservations.forEach(reservation => {
    const card = document.createElement('div');
    card.className = 'reservation-card';

    const user = usersData[reservation.user_id?.toString()];
    const customerName = user ? `${user.first_name} ${user.last_name}`.trim() : 'نامشخص';

    const staff = staffData[reservation.staff_id];
    const staffName = staff ? staff.name : 'نامشخص';

    const timeSlot = reservation.time_slot || '';
    const displayTime = timeSlot.substring(0, 5); // فقط ساعت و دقیقه

    card.innerHTML = `
        <div class="card-time">${toPersianNumber(displayTime)}</div>
        <div class="card-customer">${customerName}</div>
        <div class="card-staff">آرایشگر: ${staffName}</div>
    `;

    grid.appendChild(card);
});
}

function updateStats() {
    const weekReservations = reservationsData;
    document.getElementById('totalReservations').textContent = toPersianNumber(weekReservations.length);
    const jsDay = new Date().getDay();
    const weekDays = getCurrentWeekDaysEn();
    const todayDay = weekDays[jsDay === 6 ? 0 : jsDay + 1];
    const todayReservations = reservationsData.filter(res =>
        (res.day || "").toLowerCase() === todayDay.toLowerCase()
    );
    document.getElementById('todayReservations').textContent = toPersianNumber(todayReservations.length);
    updateServicesTicker();
}
function updateServicesTicker() {
    const tickerContent = document.getElementById('servicesTicker');
    let tickerHTML = '';
    const servicesArray = Object.values(servicesData);
    if (servicesArray.length > 0) {
        // محدود کردن تعداد خدمات برای جلوگیری از طول بیش از حد
        const limitedServices = servicesArray.slice(0, 6);
        limitedServices.forEach(service => {
            tickerHTML +=
                '<div class="ticker-item">' +
                    '<span class="service-name">' + service.name + '</span>' +
                    '<span class="service-price">' + toPersianNumber(service.price?.toLocaleString() || "۰") + ' تومان</span>' +
                '</div>';
        });
        // تکرار برای پر کردن فضا
        tickerHTML += tickerHTML;
    } else {
        tickerHTML = '<div class="ticker-item">خدماتی یافت نشد</div>';
    }
    tickerContent.innerHTML = tickerHTML;
}
function refreshData() {
    const refreshBtn = document.querySelector('.refresh-btn i');
    refreshBtn.classList.add('fa-spin');
    setTimeout(() => { refreshBtn.classList.remove('fa-spin'); }, 1000);
    loadReservationsData();
}

document.addEventListener('DOMContentLoaded', function() {
    updateWeekTitle();
    loadReservationsData();
    // بروزرسانی هر 30 ثانیه
    setInterval(loadReservationsData, 30000);
    // بروزرسانی رزروهای امروز هر دقیقه برای چک کردن زمان
    setInterval(renderTodayReservations, 60000);
});