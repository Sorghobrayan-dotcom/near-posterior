//! Forecast registry for near-posterior: a NEAR contract with no dependency.
//!
//! `commit` stores a forecast record that no method can change or delete; the block timestamp and
//! height are stored next to it. `resolve` stores one outcome per record, once, and only when the
//! block timestamp has passed the record's resolution time. Only the account that holds the
//! contract can call `commit` and `resolve`; anyone can read with `count` and `get`.
//!
//! commit input:  `<resolution unix seconds>|<record JSON>`
//! resolve input: `<index>|<outcome JSON>`
//! get input:     `<index>`
#![no_std]

const MAX: usize = 4096;
static mut IN: [u8; MAX] = [0; MAX];
static mut OUT: [u8; 3 * MAX] = [0; 3 * MAX];
static mut TMP: [u8; MAX] = [0; MAX];

#[link(wasm_import_module = "env")]
extern "C" {
    fn input(register_id: u64);
    fn register_len(register_id: u64) -> u64;
    fn read_register(register_id: u64, ptr: u64);
    fn current_account_id(register_id: u64);
    fn predecessor_account_id(register_id: u64);
    fn block_timestamp() -> u64;
    fn block_index() -> u64;
    fn value_return(value_len: u64, value_ptr: u64);
    fn panic_utf8(len: u64, ptr: u64);
    fn log_utf8(len: u64, ptr: u64);
    fn storage_write(kl: u64, kp: u64, vl: u64, vp: u64, register_id: u64) -> u64;
    fn storage_read(kl: u64, kp: u64, register_id: u64) -> u64;
}

#[panic_handler]
fn on_panic(_: &core::panic::PanicInfo) -> ! {
    core::arch::wasm32::unreachable()
}

/// Abort the call with a message.
fn fail(msg: &str) -> ! {
    unsafe { panic_utf8(msg.len() as u64, msg.as_ptr() as u64) };
    core::arch::wasm32::unreachable()
}

/// Copy register 0 into `buf` and return its length.
fn reg(buf: *mut u8) -> usize {
    let n = unsafe { register_len(0) } as usize;
    if n > MAX {
        fail("input too long");
    }
    unsafe { read_register(0, buf as u64) };
    n
}

/// Return the call input.
fn arg() -> &'static [u8] {
    unsafe {
        input(0);
        let p = core::ptr::addr_of_mut!(IN) as *mut u8;
        let n = reg(p);
        core::slice::from_raw_parts(p, n)
    }
}

/// Abort unless the caller is the contract account itself.
fn only_owner() {
    unsafe {
        let a = core::ptr::addr_of_mut!(TMP) as *mut u8;
        current_account_id(0);
        let na = reg(a);
        let me = core::slice::from_raw_parts(a, na);
        let b = a.add(na);
        predecessor_account_id(0);
        let nb = register_len(0) as usize;
        if na + nb > MAX {
            fail("account id too long");
        }
        read_register(0, b as u64);
        if me != core::slice::from_raw_parts(b, nb) {
            fail("only the contract account can write");
        }
    }
}

/// Parse an unsigned decimal number.
fn num(s: &[u8]) -> u64 {
    if s.is_empty() || s.len() > 19 {
        fail("bad number");
    }
    let mut v: u64 = 0;
    for &c in s {
        if !c.is_ascii_digit() {
            fail("bad number");
        }
        v = v * 10 + (c - b'0') as u64;
    }
    v
}

/// Split `a|b` at the first `|`.
fn split(s: &[u8]) -> (&[u8], &[u8]) {
    match s.iter().position(|&c| c == b'|') {
        Some(i) => (&s[..i], &s[i + 1..]),
        None => fail("expected <number>|<json>"),
    }
}

/// Storage key: one letter then the index as 8 little-endian bytes.
fn key(tag: u8, i: u64) -> [u8; 9] {
    let mut k = [tag; 9];
    k[1..].copy_from_slice(&i.to_le_bytes());
    k
}

fn put(k: &[u8], v: &[u8]) {
    unsafe { storage_write(k.len() as u64, k.as_ptr() as u64, v.len() as u64, v.as_ptr() as u64, 1) };
}

/// Read a stored value into TMP, or None.
fn take(k: &[u8]) -> Option<&'static [u8]> {
    unsafe {
        if storage_read(k.len() as u64, k.as_ptr() as u64, 0) == 0 {
            return None;
        }
        let p = core::ptr::addr_of_mut!(TMP) as *mut u8;
        let n = reg(p);
        Some(core::slice::from_raw_parts(p, n))
    }
}

fn count_get() -> u64 {
    match take(b"n") {
        Some(v) if v.len() == 8 => u64::from_le_bytes([v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]]),
        _ => 0,
    }
}

/// Byte writer over OUT.
struct W(usize);
impl W {
    fn b(&mut self, s: &[u8]) -> &mut Self {
        unsafe {
            let o = &mut *core::ptr::addr_of_mut!(OUT);
            if self.0 + s.len() > o.len() {
                fail("output too long");
            }
            o[self.0..self.0 + s.len()].copy_from_slice(s);
        }
        self.0 += s.len();
        self
    }
    fn n(&mut self, mut v: u64) -> &mut Self {
        let mut d = [0u8; 20];
        let mut i = 20;
        loop {
            i -= 1;
            d[i] = b'0' + (v % 10) as u8;
            v /= 10;
            if v == 0 {
                break;
            }
        }
        self.b(&d[i..])
    }
    fn done(&self) {
        unsafe { value_return(self.0 as u64, core::ptr::addr_of!(OUT) as u64) };
    }
}

fn u64_at(v: &[u8], at: usize) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&v[at..at + 8]);
    u64::from_le_bytes(b)
}

#[no_mangle]
pub extern "C" fn commit() {
    only_owner();
    let (due, rec) = split(arg());
    let due = num(due);
    let i = count_get();
    let mut meta = [0u8; 24];
    unsafe {
        meta[..8].copy_from_slice(&block_timestamp().to_le_bytes());
        meta[8..16].copy_from_slice(&block_index().to_le_bytes());
    }
    meta[16..].copy_from_slice(&due.to_le_bytes());
    put(&key(b'f', i), rec);
    put(&key(b'm', i), &meta);
    put(b"n", &(i + 1).to_le_bytes());
    let mut w = W(0);
    w.b(b"committed forecast ").n(i);
    unsafe { log_utf8(w.0 as u64, core::ptr::addr_of!(OUT) as u64) };
    W(0).n(i).done();
}

#[no_mangle]
pub extern "C" fn resolve() {
    only_owner();
    let (i, outcome) = split(arg());
    let i = num(i);
    if take(&key(b'r', i)).is_some() {
        fail("already resolved");
    }
    let due = match take(&key(b'm', i)) {
        Some(m) => u64_at(m, 16),
        None => fail("no such forecast"),
    };
    if unsafe { block_timestamp() } / 1_000_000_000 < due {
        fail("resolution date not reached");
    }
    let mut v = [0u8; MAX];
    if outcome.len() + 8 > MAX {
        fail("outcome too long");
    }
    v[..8].copy_from_slice(&unsafe { block_timestamp() }.to_le_bytes());
    v[8..8 + outcome.len()].copy_from_slice(outcome);
    put(&key(b'r', i), &v[..8 + outcome.len()]);
    W(0).n(i).done();
}

#[no_mangle]
pub extern "C" fn count() {
    W(0).n(count_get()).done();
}

#[no_mangle]
pub extern "C" fn get() {
    let i = num(arg());
    let mut w = W(0);
    let (ts, h, due) = match take(&key(b'm', i)) {
        Some(m) => (u64_at(m, 0), u64_at(m, 8), u64_at(m, 16)),
        None => fail("no such forecast"),
    };
    w.b(b"{\"index\":").n(i).b(b",\"block_timestamp_ns\":").n(ts).b(b",\"block_height\":").n(h);
    w.b(b",\"resolution_unix_s\":").n(due).b(b",\"record\":");
    w.b(take(&key(b'f', i)).unwrap_or(b"null"));
    w.b(b",\"outcome\":");
    match take(&key(b'r', i)) {
        Some(r) => {
            let t = u64_at(r, 0);
            w.b(b"{\"block_timestamp_ns\":").n(t).b(b",\"value\":").b(&r[8..]).b(b"}");
        }
        None => {
            w.b(b"null");
        }
    }
    w.b(b"}").done();
}
