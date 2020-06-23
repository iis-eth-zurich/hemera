/*
 * Copyright (C) 2018 ETH Zurich and University of Bologna
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * Authors: Germain Haugou, ETH (germain.haugou@iis.ee.ethz.ch)
 */

#include <stdarg.h>
#include "hal/pulp.h"
#include "rt/rt_api.h"
#include "hal/debug_bridge/debug_bridge.h"
#include <stdint.h>

extern int _prf(int (*func)(), void *dest,
        const char *format, va_list vargs);

#if defined(ARCHI_UDMA_HAS_UART) && UDMA_VERSION >= 2 || defined(ARCHI_HAS_UART)
#define __RT_USE_UART 1
#endif

extern char __rt_sim;
int get_rt_sim() {
  return (int)&__rt_sim == 1;
}

static RT_FC_DATA rt_fc_lock_t __rt_io_fc_lock;

#if defined(__RT_USE_UART)
static rt_uart_t *_rt_io_uart;
static rt_event_t __rt_io_event;
static rt_event_t *__rt_io_event_current;
#endif

hal_debug_struct_t HAL_DEBUG_STRUCT_NAME = HAL_DEBUG_STRUCT_INIT;

static int __rt_io_pending_flush;

static int errno;
int *__errno() { return &errno; }

static void __rt_io_unlock();
static void __rt_io_lock();

static void *domain_malloc(size_t size, int domain)
{
  void * ptr = rt_alloc(domain, size + 0x4U);
  if ((uint32_t) ptr == 0x0)
    return (void *) 0x0;
  *(uint32_t *)(ptr) = size + 0x4U;

  void *user_ptr = (void *)(((uint32_t *)ptr)+1);

  return user_ptr;
}

static void domain_free(void *ptr, int domain)
{
  void *alloc_ptr = (void *)(((uint32_t *)ptr)-1);
  uint32_t size = *((uint32_t *)alloc_ptr);
  rt_free(domain, alloc_ptr, size);
}

void *malloc(size_t size)
{
  return domain_malloc(size, RT_ALLOC_FC_DATA);
}

void free(void *ptr)
{
  domain_free(ptr, RT_ALLOC_FC_DATA);
}

void *l1malloc(size_t size)
{
  return domain_malloc(size, RT_ALLOC_CL_DATA);
}

void l1free(void *ptr)
{
  domain_free(ptr, RT_ALLOC_CL_DATA);
}

int strcmp(const char *s1, const char *s2)
{
  while (*s1 != '\0' && *s1 == *s2)
    {
      s1++;
      s2++;
    }

  return (*(unsigned char *) s1) - (*(unsigned char *) s2);
}

int strncmp(const char *s1, const char *s2, size_t n)
{
  if (n == 0)
    return 0;

  while (n-- != 0 && *s1 == *s2)
    {
      if (n == 0 || *s1 == '\0')
        break;
      s1++;
      s2++;
    }

  return (*(unsigned char *) s1) - (*(unsigned char *) s2);
}

size_t strlen(const char *str)
{
  const char *start = str;

  while (*str)
    str++;
  return str - start;
}

int memcmp(const void *m1, const void *m2, size_t n)
{
  unsigned char *s1 = (unsigned char *) m1;
  unsigned char *s2 = (unsigned char *) m2;

  while (n--)
    {
      if (*s1 != *s2)
        {
          return *s1 - *s2;
        }
      s1++;
      s2++;
    }
  return 0;
}

void *memset(void *m, int c, size_t n)
{
  char *s = (char *)m;
  while (n--)
    *s++ = (char) c;

  return m;
}

void *memcpy(void *dst0, const void *src0, size_t len0) {
  void *save = dst0;

  char src_aligned = (((size_t) src0) & 3) == 0;
  char dst_aligned = (((size_t) dst0) & 3) == 0;
  char copy_full_words = (len0 & 3) == 0;

  if (src_aligned && dst_aligned && copy_full_words) {
    // all accesses are aligned => can copy full words
    uint32_t *dst = (uint32_t *) dst0;
    uint32_t *src = (uint32_t *) src0;

    while (len0) {
      *dst++ = *src++;
      len0 -= 4;
    }
  } else {
    // copy bytewise
    char *dst = (char *) dst0;
    char *src = (char *) src0;

    while (len0) {
      *dst++ = *src++;
      len0--;
    }
  }

  return save;
}

void *memmove(void *d, const void *s, size_t n)
{
  char *dest = d;
  const char *src  = s;

  if ((size_t) (dest - src) < n) {
    /*
     * The <src> buffer overlaps with the start of the <dest> buffer.
     * Copy backwards to prevent the premature corruption of <src>.
     */

    while (n > 0) {
      n--;
      dest[n] = src[n];
    }
  } else {
    /* It is safe to perform a forward-copy */
    while (n > 0) {
      *dest = *src;
      dest++;
      src++;
      n--;
    }
  }

  return d;
}

char *strcpy(char *d, const char *s)
{
	char *dest = d;
	while (*s != '\0') {
		*d = *s;
		d++;
		s++;
	}
	*d = '\0';
	return dest;
}

char *strcat(char *dest, const char *src)
{
	strcpy(dest + strlen(dest), src);
	return dest;
}

char *strchr(const char *s, int c)
{
  char tmp = (char) c;

  while ((*s != tmp) && (*s != '\0'))
    s++;

  return (*s == tmp) ? (char *) s : NULL;
}

void __rt_putc_debug_bridge(char c)
{
  hal_debug_putchar(hal_debug_struct_get(), c);
}

static void __rt_putc_stdout(char c)
{
  if (!get_rt_sim()) {
    *(uint32_t *)(long)(ARCHI_STDOUT_ADDR + STDOUT_PUTC_OFFSET + (rt_core_id()<<3) + (rt_cluster_id()<<7)) = c;
  } else {
    *(uint32_t *)(long)(0x1D104000 + (rt_core_id() << 3) + (rt_cluster_id() << 7)) = c;
  }
}


#if defined(__RT_USE_UART)


#if defined(ARCHI_HAS_CLUSTER)

static void __rt_io_uart_wait_req(void *_req)
{
  int irq = rt_irq_disable();
  if (__rt_io_event_current)
  {
    rt_event_wait(__rt_io_event_current);
    __rt_io_event_current = NULL;
  }
  rt_io_wait_req_t *req = _req;
  rt_compiler_barrier();
  req->done = 1;
  __rt_cluster_notif_req_done(req->cid);
  rt_irq_restore(irq);
}

#endif

static void __rt_io_uart_wait_pending()
{
  while(__rt_io_pending_flush)
  {
    __rt_io_unlock();
    rt_event_yield(NULL);
    __rt_io_lock();
  }

  if (__rt_io_event_current)
  {
    if (rt_is_fc() || !rt_has_fc())
    {
      rt_event_wait(__rt_io_event_current);
      __rt_io_event_current = NULL;
    }
    else
    {
#if defined(ARCHI_HAS_CLUSTER) && defined(ARCHI_HAS_FC)
      rt_io_wait_req_t req;
      req.cid = rt_cluster_id();
      req.done = 0;
      __rt_init_event(&req.event, __rt_cluster_sched_get(), __rt_io_uart_wait_req, (void *)&req);
      __rt_event_set_pending(&__rt_io_event);
      __rt_cluster_push_fc_event(&req.event);
      while((*(volatile char *)&req.done) == 0)
      {
        eu_evt_maskWaitAndClr(1<<RT_CLUSTER_CALL_EVT);
      }
#endif
    }
  }
}

static void __rt_io_end_of_flush(void *arg)
{
  hal_debug_struct_t *debug_struct = (hal_debug_struct_t *)arg;
  __rt_io_pending_flush = 0;
  debug_struct->putc_current = 0;
}

static void __attribute__((noinline)) __rt_io_uart_flush(hal_debug_struct_t *debug_struct)
{
  while(__rt_io_pending_flush)
  {
    __rt_io_unlock();
    rt_event_yield(NULL);
    __rt_io_lock();
  }

  if (debug_struct->putc_current)
  {
    if (rt_is_fc() || !rt_has_fc())
    {
      __rt_io_pending_flush = 1;
      rt_uart_write(_rt_io_uart, debug_struct->putc_buffer,
        debug_struct->putc_current, rt_event_get(NULL, __rt_io_end_of_flush, debug_struct));

      __rt_io_unlock();

      while(__rt_io_pending_flush)
      {
        rt_event_yield(NULL);
      }

      __rt_io_lock();
    }
    else {
  #if defined(ARCHI_HAS_CLUSTER) && defined(ARCHI_HAS_FC)
      rt_uart_req_t req;
      rt_uart_cluster_write(_rt_io_uart, debug_struct->putc_buffer,
        debug_struct->putc_current, &req);
      rt_uart_cluster_wait(&req);
      debug_struct->putc_current = 0;
  #endif
    }

  }
}

void __rt_putc_uart(char c)
{
  // In case a transfer is already pending, wait for its completion
  // to not overwrite the buffer being flushed to the uart.
  __rt_io_uart_wait_pending();

  // Store the new character at the end of the buffer.
  hal_debug_struct_t *debug_struct = hal_debug_struct_get();
  debug_struct->putc_buffer[debug_struct->putc_current++] = c;

  // And flush it if we reached the maximum size or an end of line.
  if (debug_struct->putc_current == HAL_PRINTF_BUF_SIZE || c == '\n')
  {
    __rt_io_uart_flush(debug_struct);
  }
}
#endif

static void tfp_putc(void *data, char c)
{
  if (get_rt_sim()) {
    __rt_putc_stdout(c);
    return;
  }

  if (hal_debug_struct_get()->use_internal_printf)
  {
#if defined(__RT_USE_UART)
    if (_rt_io_uart)
    {
      __rt_putc_uart(c);
    }
    else
#endif
    {
      __rt_putc_stdout(c);
    }
  }
  else
  {
    __rt_putc_debug_bridge(c);
  }
}

static void __rt_io_lock()
{
  if (get_rt_sim())
    return;

#if !defined(__RT_USE_UART)
  if (hal_debug_struct_get()->use_internal_printf) return;
#else
  if (hal_debug_struct_get()->use_internal_printf && !_rt_io_uart) return;
#endif

  if (rt_is_fc() || !rt_has_fc())
  {
    __rt_fc_lock(&__rt_io_fc_lock);
  }
  else
  {
#if defined(ARCHI_HAS_CLUSTER)
    rt_fc_lock_req_t req;
    __rt_fc_cluster_lock(&__rt_io_fc_lock, &req);
    __rt_fc_cluster_lock_wait(&req);
#endif
  }
}

static void __rt_io_unlock()
{
  if (get_rt_sim())
    return;

#if !defined(__RT_USE_UART)
  if (hal_debug_struct_get()->use_internal_printf) return;
#else
  if (hal_debug_struct_get()->use_internal_printf && !_rt_io_uart) return;
#endif

  if (rt_is_fc() || !rt_has_fc())
  {
    __rt_fc_unlock(&__rt_io_fc_lock);
  }
  else
  {
#if defined(ARCHI_HAS_CLUSTER)
    rt_fc_lock_req_t req;
    __rt_fc_cluster_unlock(&__rt_io_fc_lock, &req);
    __rt_fc_cluster_lock_wait(&req);
#endif
  }
}

#if 0
int printf(const char *fmt, ...) {

  __rt_io_lock();

  va_list va;
  va_start(va, fmt);
  tfp_format(NULL, tfp_putc, fmt, va);
  va_end(va);

__rt_io_unlock();

  return 0;
}

#endif

int puts(const char *s) {

  __rt_io_lock();

  char c;
  do {
    c = *s;
    if (c == 0) {
      tfp_putc(NULL, '\n');
      break;
    }
    tfp_putc(NULL, c);
    s++;
  } while(1);

__rt_io_unlock();

  return 0;
}

int fputc_locked(int c, FILE *stream)
{
  tfp_putc(NULL, c);

  return c;
}

int fputc(int c, FILE *stream)
{
  int err;

  __rt_io_lock();

  err = fputc_locked(c, stream);

  if (!hal_debug_struct_get()->use_internal_printf)
  {
    hal_debug_send_printf(hal_debug_struct_get());
  }

__rt_io_unlock();

  return err;
}

int putchar(int c)
{
  return fputc(c, stdout);
}

int _prf_locked(int (*func)(), void *dest, char *format, va_list vargs)
{
  int err;

  __rt_io_lock();

  err =  _prf(func, dest, format, vargs);

  __rt_io_unlock();

  return err;
}

static void __attribute__((noreturn)) __wait_forever()
{
  // TODO find a better solution. On some architectures or platforms
  // the execution starts immediately and is stuck here as it is
  // impossible to force the core to leave clock-gating
#if 0
#if defined(ITC_VERSION)
  hal_itc_enable_clr(0xffffffff);
  while(1) hal_itc_wait_for_interrupt();
#elif defined(EU_VERSION) && EU_VERSION >=3
  eu_evt_maskClr(0xffffffff);
  eu_evt_wait();
#endif
#endif
  while(1);
}

static void __rt_exit_debug_bridge(int status)
{
  // Flush the pending messages to the debug tools
  // Notify debug tools about the termination
  hal_debug_send_printf(hal_debug_struct_get());
  hal_debug_exit(hal_debug_struct_get(), status);
}


#if defined(PULP_CHIP_FAMILY) && PULP_CHIP_FAMILY == CHIP_BIGPULP

void exit(int status)
{
  __rt_exit_debug_bridge(status);
  apb_soc_status_set(status);
  hal_cluster_ctrl_eoc_set(1);
  __wait_forever();
}

#elif defined(APB_SOC_VERSION) && APB_SOC_VERSION >= 2

void exit(int status)
{
  apb_soc_status_set(status);
  __rt_exit_debug_bridge(status);

  __wait_forever();
}

#else

#if defined(__ariane__)

RT_L2_DATA int tohost;

void exit(int status)
{
  __rt_exit_debug_bridge(status);
  tohost = status;
  apb_soc_status_set(status);
  __wait_forever();
}

#else

void exit(int status)
{
#if defined(ARCHI_L2_ADDR)
  *(volatile int*)(ARCHI_L2_ADDR) = status;
#endif
#if defined(ARCHI_CLUSTER_CTRL_ADDR)
  *(volatile int*)(ARCHI_CLUSTER_CTRL_ADDR) = 1;
#endif
  __rt_exit_debug_bridge(status);
  __wait_forever();
}

#endif

#endif

void abort()
{
  exit(-1);
}


#if defined(__RT_USE_UART)
static int __rt_io_start(void *arg)
{
  rt_trace(RT_TRACE_INIT, "[IO] Opening UART device for IO stream\n");

  rt_uart_conf_t conf;
  rt_uart_conf_init(&conf);

  if (rt_event_alloc(NULL, 1))
    return -1;

  conf.baudrate = rt_iodev_uart_baudrate();

  __rt_event_init(&__rt_io_event, rt_event_internal_sched());

#if defined(UDMA_VERSION)
  _rt_io_uart = __rt_uart_open(rt_iodev_uart_channel() + ARCHI_UDMA_UART_ID(0), &conf, NULL, NULL);
#else
  _rt_io_uart = __rt_uart_open(0, &conf, NULL, NULL);
#endif

  return 0;
}

static int __rt_io_stop(void *arg)
{
  rt_trace(RT_TRACE_INIT, "[IO] Closing UART device for IO stream\n");

  // When shutting down the runtime, make sure we wait until all pending
  // IO transfers are done.
  __rt_io_uart_wait_pending();

  // Also close the uart driver to properly flush the uart
  rt_uart_close(_rt_io_uart, NULL);

  _rt_io_uart = NULL;

  return 0;
}
#endif


void __rt_io_set()
{
#if defined(__RT_USE_UART)
  if (rt_iodev() == RT_IODEV_UART)
  {
    __rt_io_start(NULL);
    __rt_cbsys_add(RT_CBSYS_STOP, __rt_io_stop, NULL);
    __rt_io_pending_flush = 0;
    rt_event_alloc(NULL, 1);
  }
#endif
}

RT_FC_BOOT_CODE void __attribute__((constructor)) __rt_io_init()
{
  if (get_rt_sim())
    return;

  __rt_fc_lock_init(&__rt_io_fc_lock);

#if defined(__RT_USE_UART)
  _rt_io_uart = NULL;
  __rt_io_event_current = NULL;

  if (rt_iodev() == RT_IODEV_UART)
  {
    __rt_cbsys_add(RT_CBSYS_START, __rt_io_start, NULL);
    __rt_cbsys_add(RT_CBSYS_STOP, __rt_io_stop, NULL);
    __rt_io_pending_flush = 0;
    rt_event_alloc(NULL, 1);
  }
#endif

}