/*
 * Copyright (C) 2018 ETH Zurich and University of Bologna
 * 
 * Authors: 
 *    Alessandro Capotondi, UNIBO, (alessandro.capotondi@unibo.it)
 *    Andrea Marongiu,      UNIBO, (a.marongiu@unibo.it)
 *    Giuseppe Tagliavini,  UNIBO, (giuseppe.tagliavini@unibo.it)
 *    Germain Haugou,       ETH,   (germain.haugou@iis.ee.ethz.ch)
 */

/* Copyright (C) 2005-2014 Free Software Foundation, Inc.
 * C ontributed by Richard Henderson <r*th@redhat.com>.
 * 
 * This file is part of the GNU OpenMP Library (libgomp).
 * 
 * Libgomp is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * Libgomp is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 * 
 * Under Section 7 of GPL version 3, you are granted additional
 * permissions described in the GCC Runtime Library Exception, version
 * 3.1, as published by the Free Software Foundation.
 * 
 * You should have received a copy of the GNU General Public License and
 * a copy of the GCC Runtime Library Exception along with this program;
 * see the files COPYING3 and COPYING.RUNTIME respectively.  If not, see
 * <http://www.gnu.org/licenses/>.
 */

/* This file handles the BARRIER construct. */

#include "libgomp.h"

/* Application-level barrier */
void
GOMP_barrier()
{
#if defined(PROFILE0) && defined(TRACE_BASE_ADDR)
    pulp_trace(TRACE_OMP_BARRIER_ENTER);
#endif

    // This call for the moment is slower...25 CPU cycles compare 18
    // gomp_hal_hwBarrier( (gomp_get_curr_team ( get_proc_id( ) ))->barrier_id );
    gomp_hal_hwBarrier( (CURR_TEAM ( get_proc_id( ) ))->barrier_id );

#if defined(PROFILE0) && defined(TRACE_BASE_ADDR)
    pulp_trace(TRACE_OMP_BARRIER_EXIT);
#endif
 
}
