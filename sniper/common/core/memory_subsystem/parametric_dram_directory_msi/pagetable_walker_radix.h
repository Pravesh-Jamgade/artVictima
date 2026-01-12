    #ifndef PTWV2_H
    #define PTWV2_H

#include "page_table_walker_types.h"
#include "pagetable_walker.h"
#include "pagetable_buffer.h"
#include "cache_cntlr.h"
#include "subsecond_time.h"
#include "fixed_types.h"
#include "hit_where.h"
#include "memory_manager.h"
#include <stdint.h>
#include "utopia_cache_template.h"
#include "stats.h"
#include <vector>
#include <unordered_map>
#include <array>
#include <string>
#include <map>


    namespace ParametricDramDirectoryMSI{

    struct ProposedHistogram{
        static const int kBuckets = 20;
        std::array<UInt64, kBuckets> buckets;
        UInt64 total;
        UInt64 min;
        UInt64 max;
        ProposedHistogram() : total(0), min(0), max(0) { buckets.fill(0); }
        void update(UInt64 value);
        void print(FILE *fp, const char *label, int width = 40) const;
        void printCsv(FILE *fp, const char *metric_name) const;
    };

    class PageTableWalkerRadix: public PageTableWalker{

            public:

                struct{
                    int number_of_levels;
                    int *address_bit_indices;
                    int *hit_percentages;
                } stats_radix;

            static int counter;
            UtopiaCache* shadow_cache;
            std::vector<IntPtr> addresses;
            Core* core;
            CacheCntlr *cache;
            String name;
            PageTableWalkerRadix(int number_of_levels,Core* _core,ShmemPerfModel* _m_shmem_perf_model,int *level_bit_indices,int *level_percentages, PWC* pwc, bool pwc_enabled,UtopiaCache* shadow_cache);
            ptw_table* starting_table;
            ShmemPerfModel* m_shmem_perf_model;
            SubsecondTime *latency_per_level;
            std::vector<StatHist> latency_histograms;
            std::vector<std::unordered_map<HitWhere::where_t, UInt64>> hit_where_histograms;
            std::vector<std::unordered_map<HitWhere::where_t, SubsecondTime>> hit_where_latency;
            std::vector<UInt64> level_accesses;
            std::vector<UInt64> psc_hits_per_level;
            std::vector<UInt64> psc_misses_per_level;
            std::vector<ProposedHistogram> psc_miss_latency_histograms;
            std::vector<std::array<UInt64, HitWhere::NUM_HITWHERES>> psc_miss_hit_where_counts;
            std::vector<UInt64> rob_stall_psc_level_cycles;
            ProposedHistogram stlb_miss_latency_histogram;
            UInt64 rob_stall_stlb_miss_cycles;
            UInt64 psc_accesses;
            UInt64 psc_misses;
            std::map<std::string, UInt64> traversal_path_counts;
            UInt64 traversal_paths_unique_count;
            SubsecondTime total_walk_latency;
            SubsecondTime total_ptb_latency;
            SubsecondTime init_walk(IntPtr eip, IntPtr address, UtopiaCache* shadow_cache, CacheCntlr *_cache,Core::lock_signal_t lock_signal,Byte* data_buf, UInt32 data_length,bool modeled, bool count) ;
            SubsecondTime InitializeWalkRecursive(IntPtr eip, IntPtr address,int level,ptw_table* new_table,Core::lock_signal_t lock_signal,Byte* data_buf, UInt32 data_length,bool modeled, bool count, std::string &traversal_path, bool allow_psc_lookup);
            int init_walk_functional(IntPtr address);
            int init_walk_recursive_functional(IntPtr address,int level,ptw_table* new_table);
            bool isPageFault(IntPtr address);
            bool isPageFaultHelper(uint64_t address,int level,ptw_table* new_table);
            std::vector<IntPtr> getAddresses(){return addresses;}
            ~PageTableWalkerRadix();
        private:
            std::vector<uint64_t> computeVpnIndices(uint64_t address);
            ptw_table* resolveTableForLevel(const std::vector<uint64_t> &vpn_indices, int target_level);
            void recordLevelStats(int level_index, SubsecondTime latency, HitWhere::where_t *hit_where = NULL);
    };

    }
    #endif 
