// Copyright (c) 2018 ETH Zurich, University of Bologna
//
// Copyright and related rights are licensed under the Solderpad Hardware
// License, Version 0.51 (the "License"); you may not use this file except in
// compliance with the License.  You may obtain a copy of the License at
// http://solderpad.org/licenses/SHL-0.51. Unless required by applicable law
// or agreed to in writing, software, hardware and materials distributed under
// this License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

`ifndef APB_ASSIGN_SVH_
`define APB_ASSIGN_SVH_

// Assign an APB2 master interface to a slave interface, as in `assign slv = mst;`.
// TODO: add prot and strb on switch to APBv2
`define APB_ASSIGN(slv, mst)          \
  assign slv.paddr    = mst.paddr;    \
  assign slv.psel     = mst.psel;     \
  assign slv.penable  = mst.penable;  \
  assign slv.pwrite   = mst.pwrite;   \
  assign slv.pwdata   = mst.pwdata;   \
  assign mst.pready   = slv.pready;   \
  assign mst.prdata   = slv.prdata;   \
  assign mst.pslverr  = slv.pslverr;

`endif
