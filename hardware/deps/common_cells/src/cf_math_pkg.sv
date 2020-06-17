// Copyright 2016 ETH Zurich and University of Bologna.
// Copyright and related rights are licensed under the Solderpad Hardware
// License, Version 0.51 (the "License"); you may not use this file except in
// compliance with the License.  You may obtain a copy of the License at
// http://solderpad.org/licenses/SHL-0.51. Unless required by applicable law
// or agreed to in writing, software, hardware and materials distributed under
// this License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// cf_math_pkg: Constant Function Implementations of Mathematical Functions for HDL Elaboration
//
// This package contains a collection of mathematical functions that are commonly used when defining
// the value of constants in HDL code.  These functions are implemented as Verilog constants
// functions.  Introduced in Verilog 2001 (IEEE Std 1364-2001), a constant function (§ 10.3.5) is a
// function whose value can be evaluated at compile time or during elaboration.  A constant function
// must be called with arguments that are constants.

package cf_math_pkg;

    // Ceiled Division of Two Natural Numbers
    //
    // Returns the quotient of two natural numbers, rounded towards plus infinity.
    function automatic integer ceil_div (input longint dividend, input longint divisor);
        automatic longint remainder;

        // pragma translate_off
        `ifndef VERILATOR
        if (dividend < 0) begin
            $fatal(1, "Dividend %0d is not a natural number!", dividend);
        end

        if (divisor < 0) begin
            $fatal(1, "Divisor %0d is not a natural number!", divisor);
        end

        if (divisor == 0) begin
            $fatal(1, "Division by zero!");
        end
        `endif
        // pragma translate_on

        remainder = dividend;
        for (ceil_div = 0; remainder > 0; ceil_div++) begin
            remainder = remainder - divisor;
        end
    endfunction

    // Ceiled Binary Logairthm of a Natural Number
    //
    // Returns the binary logarithm (i.e., the logarithm to the base 2) of a natural number rounded
    // towards plus infinity.  Use this as drop-in replacement for the `$clog2` system function
    // where the latter is not supported by your tools.
    function automatic int unsigned clog2(input longint unsigned val);
        longint unsigned tmp;

        // pragma translate_off
        `ifndef VERILATOR
        if (val == 0) begin
            $fatal(1, "Logarithm of 0 cannot be represented!");
        end
        `endif
        // pragma translate_on

        tmp = val - 1;
        for (clog2 = 0; tmp > 0; clog2++) begin
            tmp >>= 1;
        end
    endfunction

endpackage
